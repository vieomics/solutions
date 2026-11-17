#!/usr/bin/env python3
"""Build the HTML analysis summary and the variant-focused report."""

from __future__ import annotations

import argparse
import csv
import html
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path


def read_tsv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def esc(value) -> str:
    return html.escape(str(value))


def table(rows: list[dict], fields: list[str] | None = None, limit: int | None = None) -> str:
    if not rows:
        return "<p><em>No rows.</em></p>"
    fields = fields or list(rows[0].keys())
    body = []
    for row in rows[:limit] if limit else rows:
        body.append("<tr>" + "".join(f"<td>{esc(row.get(field, ''))}</td>" for field in fields) + "</tr>")
    head = "<tr>" + "".join(f"<th>{esc(field)}</th>" for field in fields) + "</tr>"
    return f"<table><thead>{head}</thead><tbody>{''.join(body)}</tbody></table>"


def metric_table(rows: list[dict], fields: list[str]) -> str:
    return table(rows, fields)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    args = parser.parse_args()
    results = Path(args.results)

    mapping = read_tsv(results / "mapping" / "mapping_stats.tsv")
    consensus = read_tsv(results / "consensus" / "consensus_stats.tsv")
    variants = read_tsv(results / "variants" / "nucleotide_variants.tsv")
    amino = read_tsv(results / "variants" / "amino_acid_variants.tsv")
    closest = read_tsv(results / "variants" / "closest_references.tsv")
    mutation_summary = read_tsv(results / "variants" / "mutation_summary.tsv")
    alignment = dict(
        line.split(": ", 1)
        for line in (results / "alignment" / "alignment_stats.txt").read_text().splitlines()
        if ": " in line
    )
    iqtree = (results / "hbv_phylogeny.iqtree").read_text(errors="replace")
    model_match = re.search(r"Best-fit model according to BIC:\s*(\S+)", iqtree)
    model = model_match.group(1) if model_match else "not parsed"
    phipack = (results / "recombination" / "phipack.txt").read_text(errors="replace")
    phi = re.search(r"PHI \(Permutation\):\s*(\S+)", phipack)
    maxchi = re.search(r"Max Chi\^2:\s*(\S+)", phipack)
    nss = re.search(r"NSS:\s*(\S+)", phipack)

    sample_count = len(mapping)
    public_count = sum(1 for row in read_tsv(results / "comparative" / "all_hbv_metadata.tsv") if row["record_type"] == "public_reference")
    total_variants = len(variants)
    aa_counts = Counter(row["effect"] for row in amino)
    high_n = [row for row in consensus if float(row["n_fraction"] or 0) > 0.05]

    generated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    variant_rows = []
    priority = {"stop_gained": 0, "nonsynonymous": 1, "uncertain": 2, "synonymous": 3}
    for row in sorted(
        amino,
        key=lambda row: (
            priority.get(row["effect"], 9),
            -int(float(row["depth"] or 0)),
            row["sample"],
            row["region"],
            int(row["codon"]),
        ),
    )[:30]:
        variant_rows.append(
            {
                "sample": row["sample"],
                "region": row["region"],
                "aa_change": row["aa_change"],
                "effect": row["effect"],
                "nucleotide": row["nucleotide_changes"],
                "depth": row["depth"],
                "reference": row["reference_used"],
            }
        )

    effect_rows = [{"effect": k, "count": v} for k, v in sorted(aa_counts.items())]
    region_counts = Counter()
    for row in mutation_summary:
        if row["region"] in {"S", "P", "C", "X"} and row["effect"] != "intergenic":
            region_counts[row["region"]] += int(row["count"])

    warnings = ""
    if high_n:
        warnings = (
            "<div class='warn'><strong>Partial genomes:</strong> "
            + ", ".join(
                f"{esc(row['sample'])} ({float(row['n_fraction']):.1%} N; breadth ≥10× {esc(row['breadth_10x_pct'])}%)"
                for row in high_n
            )
            + ". These samples carry a large low-coverage block and are not complete genomes."
            "</div>"
        )

    html_text = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>HBV whole-genome analysis summary</title>
<style>
  :root {{ color-scheme: light; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
         max-width: 1120px; margin: 0 auto; padding: 2rem 1.25rem 4rem; color: #1f2933; line-height: 1.55; }}
  h1, h2, h3 {{ color: #102a43; line-height: 1.2; }}
  h1 {{ margin-bottom: 0.2rem; }}
  .sub {{ color: #52606d; margin-top: 0; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 0.8rem; margin: 1rem 0; }}
  .card {{ border: 1px solid #d9e2ec; border-radius: 8px; padding: 0.8rem 1rem; background: #f8fafc; }}
  .card b {{ display: block; font-size: 1.35rem; color: #0b7285; }}
  .warn {{ border-left: 4px solid #d97706; background: #fffbeb; padding: 0.7rem 1rem; margin: 1rem 0; }}
  .note {{ border-left: 4px solid #2563eb; background: #eff6ff; padding: 0.7rem 1rem; margin: 1rem 0; }}
  table {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; margin: 0.7rem 0 1.4rem; }}
  th, td {{ border-bottom: 1px solid #e4e7eb; padding: 0.35rem 0.45rem; text-align: left; vertical-align: top; }}
  th {{ background: #f0f4f8; position: sticky; top: 0; }}
  img {{ max-width: 100%; height: auto; border: 1px solid #e4e7eb; border-radius: 6px; margin: 0.5rem 0 1rem; }}
  code {{ background: #f0f4f8; padding: 0.1rem 0.25rem; border-radius: 3px; }}
  .small {{ font-size: 0.85rem; color: #52606d; }}
  a {{ color: #0b7285; }}
</style>
</head>
<body>
<h1>HBV whole-genome analysis</h1>
<p class="sub">Five Illumina samples from PRJNA659786 (Brazil) plus {public_count} public complete HBV genomes.
Generated {generated}.</p>

<div class="grid">
  <div class="card"><span>Study samples</span><b>{sample_count}</b></div>
  <div class="card"><span>Public references</span><b>{public_count}</b></div>
  <div class="card"><span>Nucleotide variant rows</span><b>{total_variants}</b></div>
  <div class="card"><span>Nonsynonymous AA changes</span><b>{aa_counts.get('nonsynonymous', 0)}</b></div>
  <div class="card"><span>Alignment length</span><b>{esc(alignment.get('alignment_length', 'NA'))} bp</b></div>
  <div class="card"><span>Best model</span><b>{esc(model)}</b></div>
</div>

{warnings}

<h2>1. Data and reference panel</h2>
<p>The five runs were selected from PRJNA659786 (three genotype A and two genotype D samples; Brazil, 2014–2015).
The public panel contains ten complete GenBank genomes: two genotype A, two B (Vietnam/Cambodia), two C (Cambodia),
three D (including the RefSeq mapping reference NC_003977.2), one E and one F. Public genomes were rotated to the
NC_003977.2 origin using a unique 25-mer vote; accessions, country, date and rotation offsets are in
<a href="references/hbv_metadata.tsv">references/hbv_metadata.tsv</a>.</p>
<p class="small">The panel is a demonstration set, not a representative sample of global HBV diversity.</p>

<h2>2. Sequencing QC</h2>
<img src="figures/qc_summary.png" alt="FastQC/fastp QC summary">
<p>MultiQC report: <a href="qc/multiqc_report.html">qc/multiqc_report.html</a>. FastQC outputs are in
<a href="qc/fastqc/">qc/fastqc/</a>, fastp reports in <a href="trimmed/">trimmed/</a>.</p>

<h2>3. Mapping and genome coverage</h2>
<img src="figures/genome_coverage.png" alt="Circular HBV coverage">
<p>Reads were mapped with BWA-MEM to an origin-extended reference (NC_003977.2 + first 500 bp duplicated at the 3′ end).
Positions in the duplicated tail were projected modulo 3,182 bp, so depth and allele counts represent the circular genome.
The table reports BWA mapping rate, mean depth, breadth at ≥10× and the number of reads spanning the origin.</p>
{metric_table(mapping, ['sample', 'genotype', 'bwa_mapping_rate', 'mean_depth', 'breadth_10x_pct', 'origin_spanning_reads', 'consensus_n_bases'])}

<h2>4. Consensus genomes</h2>
<p>Consensus sequences come from the nf-core/viralrecon bcftools path (variants with allele fraction ≥0.75, depth ≥10;
positions below 10× masked as N), then boundary Ns are patched with circular evidence. The two partial genomes below
are reported as partial, not as complete genomes.</p>
{metric_table(consensus, ['sample', 'genotype', 'consensus_length', 'n_bases', 'n_fraction', 'breadth_10x_pct', 'interpretation'])}
<p class="small">Validation: the P, S, C and X reference coding sequences translate exactly to the
GenBank <code>/translation</code> qualifiers (terminal stop excluded).</p>

<h2>5. Phylogeny</h2>
<img src="figures/phylogenetic_tree.png" alt="Maximum-likelihood HBV tree">
<p>IQ-TREE 2.4.0, ModelFinder best model <code>{esc(model)}</code>, 1,000 ultrafast bootstrap replicates and
1,000 SH-aLRT replicates. The tree is rooted on the genotype F sequence for display; branch lengths and support values
are preserved in <a href="hbv_phylogeny.treefile">hbv_phylogeny.treefile</a> and
<a href="hbv_phylogeny.rooted.treefile">hbv_phylogeny.rooted.treefile</a>.</p>
<p>PhiPack recombination screen: PHI permutation p = {esc(phi.group(1) if phi else 'NA')}, NSS p = {esc(nss.group(1) if nss else 'NA')},
Max Chi² p = {esc(maxchi.group(1) if maxchi else 'NA')}. The signal is significant, but missing data and the two large
low-coverage blocks can inflate recombination tests. Region-specific S and P trees were therefore built and are provided
in <a href="phylogeny/S/">phylogeny/S/</a> and <a href="phylogeny/P/">phylogeny/P/</a>. The major genotype clades are
consistent, but within-clade relationships differ between regions. A single whole-genome tree should not be over-interpreted
as evidence of transmission or recombination breakpoints.</p>
<p>Alignment: <a href="alignment/hbv_alignment.fasta">alignment/hbv_alignment.fasta</a>;
{esc(alignment.get('variable_sites', 'NA'))} variable sites, {esc(alignment.get('parsimony_informative_sites', 'NA'))} parsimony-informative sites,
gap fraction {esc(alignment.get('gap_fraction', 'NA'))}. No alignment columns were removed.</p>

<h2>6. Variation and mutation profile</h2>
<img src="figures/mutation_summary.png" alt="Mutation summary">
<p>Variants are called relative to the closest public genome (genotype-matched context) and expressed in NC_003977.2
coordinates. Overlapping reading frames are annotated independently. Counts by major region: S={region_counts['S']},
P={region_counts['P']}, C={region_counts['C']}, X={region_counts['X']}. Full tables:
<a href="variants/nucleotide_variants.tsv">nucleotide_variants.tsv</a>,
<a href="variants/amino_acid_variants.tsv">amino_acid_variants.tsv</a>,
<a href="variants/indel_variants.tsv">indel_variants.tsv</a>.
A variant-focused page is at <a href="variants/mutation_summary.html">variants/mutation_summary.html</a>.</p>
{metric_table(variant_rows, ['sample', 'region', 'aa_change', 'effect', 'nucleotide', 'depth'])}

<h2>7. Interpretation and limitations</h2>
<ul>
<li>Three genotype A and two genotype D genomes are placed consistently with the public genotype A and D references.</li>
<li>B575/2014 and B364/2014 carry large low-coverage blocks (63.8% and 83.2% breadth at ≥10×). Their consensus sequences are
partial; phylogenetic placement and variant counts for these samples are less certain.</li>
<li>The recombination test is positive; this is expected for HBV and can also reflect missing data. Region-specific trees
are provided rather than claiming a recombinant breakpoint from a single whole-genome tree.</li>
<li>No clinical interpretation is made. Variants are classified as synonymous, nonsynonymous, stop-gained or uncertain;
they are not labelled drug-resistant or immune-escape without a validated HBV database and phenotype evidence.</li>
<li>The public panel is ten genomes selected for a demonstration. It cannot support epidemiological or geographic-origin claims.</li>
</ul>

<h2>8. Reproducibility</h2>
<p>Software: <a href="software_versions.tsv">software_versions.tsv</a>. Manifest:
<a href="reproducibility_manifest.json">reproducibility_manifest.json</a>. Execution report:
<a href="workflow_execution_report.md">workflow_execution_report.md</a>. The environment is pinned by
<code>pixi.lock</code>; the nf-core pipeline is pinned at viralrecon 2.6.0 and the Nextflow version used for it is 24.10.6.</p>
<p class="small">Figure/table values are generated from the files in this results directory. The analysis is a demonstration,
not a clinical or epidemiological study.</p>
</body>
</html>
"""
    (results / "analysis_summary.html").write_text(html_text)

    variant_page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>HBV mutation summary</title>
<style>body{{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Arial,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#1f2933}}table{{border-collapse:collapse;width:100%;font-size:.86rem}}th,td{{border-bottom:1px solid #e4e7eb;padding:.35rem .45rem;text-align:left}}th{{background:#f0f4f8}}img{{max-width:100%}}</style>
</head><body>
<h1>HBV nucleotide and amino-acid variants</h1>
<p class="small">Variants relative to the closest curated public genome; coordinates are NC_003977.2 (1-based). No clinical interpretation.</p>
<img src="../figures/mutation_summary.png" alt="Mutation summary">
<h2>Closest reference per sample</h2>
{table(closest)}
<h2>Effect counts</h2>
{table(effect_rows, ['effect', 'count'])}
<h2>Top amino-acid changes</h2>
{table(variant_rows, ['sample', 'region', 'aa_change', 'effect', 'nucleotide', 'depth', 'reference'])}
<h2>All nucleotide variants</h2>
{table(variants, ['sample', 'position', 'reference_base', 'alternate_base', 'regions', 'region', 'aa_change', 'effect', 'depth'])}
<p><a href="../analysis_summary.html">Back to analysis summary</a></p>
</body></html>
"""
    (results / "variants" / "mutation_summary.html").write_text(variant_page)
    print("wrote results/analysis_summary.html and results/variants/mutation_summary.html")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
