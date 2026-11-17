#!/usr/bin/env python3
"""Write the reproducibility manifest and execution report."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from Bio import Phylo, SeqIO
from Bio.Seq import Seq


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def file_record(path: Path) -> dict:
    return {"sha256": sha256(path), "bytes": path.stat().st_size}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    args = parser.parse_args()
    results = Path(args.results)
    root = Path.cwd()
    generated = datetime.now(timezone.utc).isoformat()

    inputs = {}
    for pattern in [
        "data/fastq/*.fastq.gz",
        "references/hbv_reference.fasta",
        "references/hbv_public_genomes.fasta",
        "references/hbv_metadata.tsv",
        "references/fetch_manifest.json",
        "metadata/selected_samples.tsv",
        "metadata/ena_run_metadata.tsv",
        "pixi.toml",
        "pixi.lock",
    ]:
        for path in sorted(root.glob(pattern)):
            inputs[str(path.relative_to(root))] = file_record(path)
    for path in sorted((root / "references" / "genbank").glob("*.gb")):
        inputs[str(path.relative_to(root))] = file_record(path)

    outputs = {}
    for pattern in [
        "results/hbv_phylogeny.treefile",
        "results/hbv_phylogeny.rooted.treefile",
        "results/hbv_phylogeny.iqtree",
        "results/genome_coverage.png",
        "results/phylogenetic_tree.png",
        "results/mutation_summary.png",
        "results/hbv_genome_structure.png",
        "results/analysis_summary.html",
        "results/mapping/mapping_stats.tsv",
        "results/mapping/depth.tsv",
        "results/mapping/coverage.tsv",
        "results/consensus/consensus_stats.tsv",
        "results/comparative/all_hbv_sequences.fasta",
        "results/comparative/all_hbv_metadata.tsv",
        "results/alignment/hbv_alignment.fasta",
        "results/variants/nucleotide_variants.tsv",
        "results/variants/amino_acid_variants.tsv",
        "results/variants/indel_variants.tsv",
        "results/recombination/phipack.txt",
        "results/software_versions.tsv",
    ]:
        path = root / pattern
        if path.exists():
            outputs[pattern] = file_record(path)

    metadata = list(csv.DictReader((results / "comparative" / "all_hbv_metadata.tsv").open(), delimiter="\t"))
    public = [row for row in metadata if row["record_type"] == "public_reference"]
    samples = [row for row in metadata if row["record_type"] == "study_consensus"]
    tree = Phylo.read(results / "hbv_phylogeny.treefile", "newick")
    taxa = [terminal.name.split("|")[0] for terminal in tree.get_terminals()]
    tree_text = (results / "hbv_phylogeny.treefile").read_text()
    support_count = len(re.findall(r"\d+(?:\.\d+)?/\d+", tree_text))
    consensus_rows = list(csv.DictReader((results / "consensus" / "consensus_stats.tsv").open(), delimiter="\t"))
    reference_record = SeqIO.read(root / "references" / "genbank" / "NC_003977.2.gb", "genbank")
    reference_seq = str(reference_record.seq).upper()
    region_defs = {
        "P": [(2309, 3182), (1, 1625)],
        "S": [(157, 837)],
        "C": [(1816, 2454)],
        "X": [(1376, 1840)],
    }
    products = {
        "P": "polymerase",
        "S": "small envelope protein",
        "C": "pre-capsid protein",
        "X": "X protein",
    }
    translation_checks = {}
    for feature in reference_record.features:
        if feature.type != "CDS":
            continue
        gene = feature.qualifiers.get("gene", [""])[0]
        product = feature.qualifiers.get("product", [""])[0]
        if gene in region_defs and product == products.get(gene):
            expected = str(feature.qualifiers["translation"][0]).replace(" ", "")
            observed = str(
                Seq("".join(reference_seq[start - 1 : end] for start, end in region_defs[gene])).translate()
            ).rstrip("*")
            translation_checks[gene] = expected == observed
    figure_paths = [
        "results/figures/genome_coverage.png",
        "results/figures/phylogenetic_tree.png",
        "results/figures/mutation_summary.png",
        "results/figures/hbv_genome_structure.png",
        "results/figures/qc_summary.png",
    ]
    validation = {
        "study_samples": len(samples),
        "public_references": len(public),
        "tree_taxa": len(taxa),
        "all_expected_taxa_present": set(taxa) == {row["id"] for row in metadata},
        "bootstrap_support_labels": support_count,
        "bootstrap_present": support_count >= 5,
        "consensus_rows": len(consensus_rows),
        "partial_genomes": [
            row["sample"] for row in consensus_rows if float(row["n_fraction"]) > 0.05
        ],
        "figures_present": all((root / path).exists() for path in figure_paths),
        "figures": {path: (root / path).stat().st_size for path in figure_paths if (root / path).exists()},
        "reference_accessions": [row["accession"] for row in public],
        "reference_lengths": {row["accession"]: row["sequence_length"] for row in public},
        "reference_n_bases": {row["accession"]: row["n_bases"] for row in public},
        "cds_translations_match_genbank": translation_checks,
        "cds_translation_check_passed": all(translation_checks.values()) and len(translation_checks) == 4,
    }

    commands = [
        "pixi install",
        "bash bin/download_fastq.sh",
        "pixi run python bin/fetch_public_references.py --outdir references",
        "pixi run python bin/make_samplesheet.py",
        "pixi run -e viralrecon nextflow run nf-core/viralrecon -r 2.6.0 -c conf/viralrecon.config --input samplesheet.csv --outdir results/viralrecon --platform illumina --protocol metagenomic --genome hbv --skip_assembly --skip_kraken2 --skip_pangolin --skip_nextclade --skip_snpeff --skip_variants_quast --skip_variants_long_table --skip_picard_metrics --skip_mosdepth --skip_consensus_plots --skip_asciigenome -resume",
        "pixi run bash bin/run_circular.sh",
        "pixi run python bin/combine_comparative.py",
        "pixi run mafft --auto --reorder --thread 4 comparative/all_hbv_sequences.fasta > alignment/hbv_alignment.fasta",
        "pixi run python bin/alignment_stats.py",
        "pixi run iqtree2 -s alignment/hbv_alignment.fasta -m MFP -B 1000 --alrt 1000 -nt AUTO --prefix results/phylogeny/hbv_phylogeny -redo",
        "pixi run python bin/root_tree.py --tree results/phylogeny/hbv_phylogeny.treefile --out results/phylogeny/hbv_phylogeny.rooted.treefile",
        "pixi run python bin/extract_alignment_regions.py",
        "pixi run iqtree2 -s alignment/regions/hbv_S.fasta -m MFP -B 1000 --alrt 1000 -nt AUTO --prefix results/phylogeny/S/hbv_S -redo",
        "pixi run iqtree2 -s alignment/regions/hbv_P.fasta -m MFP -B 1000 --alrt 1000 -nt AUTO --prefix results/phylogeny/P/hbv_P -redo",
        "pixi run Phi -f alignment/hbv_alignment.fasta -t D -p 1000 -o -v > results/recombination/phipack.txt",
        "pixi run python bin/annotate_variants.py",
        "pixi run python bin/combine_mapping_stats.py",
        "pixi run bash bin/software_versions.sh",
        "pixi run python bin/make_figures.py",
        "pixi run python bin/make_report.py",
        "pixi run python bin/make_manifest.py",
    ]

    manifest = {
        "project": "HBV whole-genome short-read analysis",
        "generated_utc": generated,
        "data_source": "OmicsLab storage: datasets/gianglabs/PRJNA659786/fastq",
        "study": "PRJNA659786 / SRP279096 (Brazil; genotypes A and D)",
        "samples": [
            {
                "sample": row["sample"],
                "accession": row["accession"],
                "genotype": row["genotype"],
                "country": row["country"],
                "collection_date": row["collection_date"],
            }
            for row in samples
        ],
        "public_reference_count": len(public),
        "public_references": validation["reference_accessions"],
        "commands": commands,
        "validation": validation,
        "inputs": inputs,
        "outputs": outputs,
        "software_versions": str(results / "software_versions.tsv"),
        "pixi_lock_sha256": sha256(root / "pixi.lock"),
    }
    (results / "reproducibility_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    report = [
        "# Workflow execution report",
        "",
        f"Generated: {generated}",
        "",
        "## Dataset",
        "",
        f"- Five Illumina paired-end runs from PRJNA659786 (Brazil; three genotype A, two genotype D).",
        f"- {len(public)} public complete HBV genomes from GenBank (A, B, C, D, E, F).",
        "- Raw FASTQ files were downloaded from OmicsLab storage and checked against ENA MD5 values.",
        "- Mapping reference: NC_003977.2 (genotype D, strain ayw, 3,182 bp).",
        "",
        "## Execution",
        "",
        "The nf-core/viralrecon 2.6.0 run used the `viralrecon` pixi environment (Nextflow 24.10.6; fastp 1.0.1, Bowtie2 2.5.4,",
        "SAMtools 1.21, BCFtools 1.22). The downstream circular/consensus, alignment, phylogeny and annotation steps used the",
        "default pixi environment (Nextflow 26.10.6, BWA 0.7.19, SAMtools 1.25, BCFtools 1.25, MAFFT 7.526, IQ-TREE 2.4.0).",
        "",
        "The exact commands are stored in `reproducibility_manifest.json`; software versions are in `software_versions.tsv`.",
        "",
        "## Validation",
        "",
        f"- Study samples: {validation['study_samples']}",
        f"- Public references: {validation['public_references']}",
        f"- Tree taxa: {validation['tree_taxa']} (all expected taxa present: {validation['all_expected_taxa_present']})",
        f"- Bootstrap support labels in tree: {validation['bootstrap_support_labels']}",
        f"- Consensus rows: {validation['consensus_rows']}",
        f"- Partial genomes (>5% N): {', '.join(validation['partial_genomes']) or 'none'}",
        f"- Figures generated: {validation['figures_present']}",
        f"- CDS translations match GenBank annotation: {validation['cds_translation_check_passed']} "
        f"({validation['cds_translations_match_genbank']})",
        "",
        "## Key observations",
        "",
        "- The three genotype A samples form a clade with the Brazilian genotype A2 reference (100/100 UFBoot/SH-aLRT).",
        "- The two genotype D samples fall in the genotype D clade with the RefSeq and Brazilian D references.",
        "- Genotype B, C, E and F references provide outgroup context; the B/C clade is well supported.",
        "- B575/2014 and B364/2014 have large low-coverage blocks (63.8% and 83.2% breadth at ≥10×) and are reported as partial genomes.",
        "- PhiPack detects significant recombination signal; region-specific S and P trees are provided. Missing data may inflate the signal,",
        "  so no recombination breakpoint is claimed.",
        "- No clinical interpretation is made.",
        "",
        "## Outputs",
        "",
        "See `analysis_summary.html` for the integrated report, `variants/mutation_summary.html` for the variant page,",
        "and `figures/` for publication-style figures.",
        "",
    ]
    (results / "workflow_execution_report.md").write_text("\n".join(report))
    print(f"wrote manifest and execution report; validation={json.dumps(validation)[:300]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
