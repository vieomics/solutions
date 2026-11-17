# HBV whole-genome short-read analysis

Reproducible analysis of five Illumina HBV whole-genome sequencing runs from
NCBI BioProject [PRJNA659786](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA659786)
plus ten curated complete GenBank genomes. The deliverable includes a
stock `nf-core/viralrecon` run, MAFFT alignment, IQ-TREE 2 phylogeny and
variant tables. The step-by-step guide is this README; the reference outputs
are in `results/`.

## Prepared material in the public workspace

`s3://omicslab/data/analysis/PRJNA659786/` contains the read-only inputs used
by the platform job and the downstream steps:

| Workspace file | Source in this repo | Purpose |
|---|---|---|
| `samplesheet.csv` | `metadata/samplesheet.platform.csv` | five samples with S3 FASTQ paths |
| `viralrecon.config` | `conf/viralrecon.platform.config` | HBV reference and module settings |
| `viralrecon.omxa.json` | `manifests/viralrecon.hbv.omxa.json` | platform analysis-job manifest |
| `references/hbv_reference.fasta` | `references/hbv_reference.fasta` | NC_003977.2 mapping reference |
| `references/hbv_public_genomes.fasta` | `references/hbv_public_genomes.fasta` | ten curated GenBank genomes |
| `references/hbv_metadata.tsv` | `references/hbv_metadata.tsv` | genotype, country and date metadata |
| `references/genbank/` | `references/genbank/` | GenBank flat files |
| `metadata/` | `metadata/` | selected runs and ENA metadata |

Users can launch the job directly from the public inputs, or copy the material
into their own workspace with download + upload:

```bash
omx download -r analysis/PRJNA659786 prepared \
  -w c669cc81-d096-4679-a9a2-03329167b71f -y

omx upload prepared analysis/PRJNA659786 -w "$WORKSPACE" -y
```

For the local downstream steps, download only the references and metadata:

```bash
omx download -r analysis/PRJNA659786/references references \
  -w c669cc81-d096-4679-a9a2-03329167b71f -y
omx download -r analysis/PRJNA659786/metadata metadata \
  -w c669cc81-d096-4679-a9a2-03329167b71f -y
```

## Two ways to use this solution

This solution is deliberately split so the platform does the heavy nf-core work
and the scientist keeps an interactive downstream environment:

1. **nf-core/viralrecon as an OmicsLab analysis job.** The five public FASTQ
   pairs stay in the public OmicsLab bucket. `manifests/viralrecon.hbv.omxa.json`
   launches viralrecon on public GreenNode compute using the marketplace GitHub
   credential. The public workspace and credential UUIDs are fixed; only
   `OMICSLAB_TOKEN` is needed.
2. **Downstream analysis in OmicsLab Studio or on your local computer.** After
   the analysis job completes, download its results with `omx download` and run
   the alignment, phylogeny, variant table and figure steps interactively in a
   Studio terminal (VS Code-like) or locally with `pixi shell`.

No nf-core pipeline runs locally in the current model.

## What is in this solution

```text
hbv-genome-short-read-analysis/
├── README.md
├── pixi.toml / pixi.lock          # pinned downstream environment
├── metadata/
│   ├── selected_samples.tsv       # five runs and ENA/SRA metadata
│   ├── samplesheet.platform.csv   # public-bucket viralrecon samplesheet
│   ├── ena_run_metadata.tsv       # project metadata snapshot
│   └── samplesheet.csv            # original nf-core/fetchngs-style sheet
├── references/
│   ├── hbv_reference.fasta        # NC_003977.2 (genotype D, strain ayw)
│   ├── hbv_public_genomes.fasta   # 10 public genomes, origin-normalised
│   ├── hbv_metadata.tsv           # accessions, genotype, country, date, QC
│   ├── reference_selection.md
│   ├── fetch_manifest.json
│   └── genbank/                   # cached GenBank flat files
├── conf/
│   └── viralrecon.platform.config # platform HBV reference
├── results/                       # platform results + downstream analysis
└── manifests/                     # summary tables + platform job manifest
```

## Data

Five runs were selected from PRJNA659786: the three genotype A and two genotype D
runs with the largest read counts.

| Sample | Run | Genotype | Country | Date |
|---|---|---|---|---|
| B215/2014 | SRR12535947 | A | Brazil | 2014-04-15 |
| B575/2014 | SRR12535935 | A | Brazil | 2014-11-04 |
| B3392/2014 | SRR12535942 | A | Brazil | 2014-10-03 |
| B2719/2015 | SRR12535933 | D | Brazil | 2014-01-28 |
| B364/2014 | SRR12535938 | D | Brazil | 2014-07-03 |

Raw FASTQ files stay in the public OmicsLab bucket and are read directly by the
platform viralrecon job. Do not download them locally; download only the
`viralrecon/hbv/results` output for the downstream analysis. The five runs are
already staged in the workspace, so `nf-core/fetchngs` is not required for this
solution. If an independent ENA/SRA re-download is wanted, the five SRR
accessions above can be supplied to `nf-core/fetchngs` 1.13.0.
The reference panel is ten complete GenBank genomes:

```text
NC_003977.2  D   RefSeq / mapping reference
KJ854710.1   A2  Brazil 2007
MF674515.1   B4  Vietnam 2014
LC456127.1   B2  Cambodia 2011
LC456135.1   C1  Cambodia 2013
LC535950.1   C1  Cambodia 2017
MH724251.1   D4  Brazil 2004
MH724252.1   D1  Brazil 2012
PZ495693.1   E   Kenya 2023
MK183647.1   F4  Paraguay 2017
```

`NC_003977.2` is the ayw strain and **genotype D**; it is used as the common
mapping coordinate frame. Public genomes were rotated to its origin by a unique
25-mer vote before alignment.

## Quick start

### A. Launch nf-core/viralrecon as an analysis job

The **public** OmicsLab workspace holds the prepared, read-only material:

```text
s3://omicslab/data/analysis/PRJNA659786/
├── samplesheet.csv
├── viralrecon.config
├── viralrecon.omxa.json
├── metadata/
│   ├── selected_samples.tsv
│   └── ena_run_metadata.tsv
└── references/
    ├── hbv_reference.fasta
    ├── hbv_public_genomes.fasta
    ├── hbv_metadata.tsv
    ├── accessions.txt
    ├── reference_selection.md
    ├── fetch_manifest.json
    └── genbank/*.gb
```

Each user runs the job in **their own workspace**; the manifest uses the public
samplesheet/config and a relative `outdir` (`viralrecon/hbv/results`), which the
platform resolves to the user’s bucket. The large FASTQ files stay in the public
bucket:

```text
s3://omicslab/data/datasets/gianglabs/PRJNA659786/fastq/
```

The marketplace GitHub UUID (`521f11ad-4269-4d87-a047-701922bd98e4`) and
GreenNode compute UUID (`c257676b-b5b6-42af-ac1c-84cd6e68b2c2`) are fixed in
`manifests/viralrecon.hbv.omxa.json`.

Use the OmicsLab SDK shell for the platform CLI. Run this from your platform
checkout, which defines the `sdk` environment; the pixi environment in this
solution does not include the SDK:

```bash
pixi shell -e sdk
```

Then run the following from this solution directory:

```bash
export OMICSLAB_TOKEN='<token>'
export WORKSPACE='<workspace-uuid>'

omx ws analysis config upload manifests/viralrecon.hbv.omxa.json \
  --key analysis/PRJNA659786/viralrecon.omxa.json -w "$WORKSPACE"

omx ws analysis config launch analysis/PRJNA659786/viralrecon.omxa.json \
  -w "$WORKSPACE"
```

The manifest runs **8 CPU / 16 GB / 20 GB / 2 h** on public GreenNode compute
with the marketplace GitHub credential. Results are written under:

```text
s3://<user-bucket>/data/viralrecon/hbv/results
```

Download them with:

```bash
omx download "viralrecon/hbv/results" results/viralrecon \
  -w "$WORKSPACE" -y
```

The public material is read-only. To copy it into your own workspace, use the
download + upload block under
[Prepared material in the public workspace](#prepared-material-in-the-public-workspace).

The platform job uses `nf-core/viralrecon` at the pinned `dev` commit compatible
with the platform Nextflow runtime. No nf-core pipeline runs locally.

### B. Analyse the results with Python

The platform job writes the consensus sequences to
`results/viralrecon/variants/bcftools/consensus/bcftools/`. Install the local
tools and run the commands below from the solution root:

```bash
pixi install
pixi shell
```

**Step 1 — combine the five consensus genomes with the ten public genomes.**

```python
import csv
from pathlib import Path
from Bio import SeqIO

outdir = Path("results/downstream")
outdir.mkdir(parents=True, exist_ok=True)

# Five viralrecon consensus genomes plus ten public GenBank genomes.
records = []
for path in sorted(Path("results/viralrecon/variants/bcftools/consensus/bcftools").glob("*.consensus.fa")):
    for record in SeqIO.parse(path, "fasta"):
        record.id = record.id.replace(" ", "_")
        record.description = ""
        records.append(record)
for record in SeqIO.parse("references/hbv_public_genomes.fasta", "fasta"):
    # Keep the pipe-separated metadata, but replace spaces so the identifier
    # survives Newick/FASTA parsing. "not available" becomes "not_available".
    record.id = record.description.replace(" ", "_")
    record.description = ""
    records.append(record)
SeqIO.write(records, outdir / "all_hbv_sequences.fasta", "fasta")

# Metadata used to label and colour the tree.
metadata = []
with open("metadata/selected_samples.tsv") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        metadata.append({
            "id": row["sample"],
            "record_type": "study_consensus",
            "genotype": row["genotype"],
            "isolate": row["alias"],
            "country": row["country"],
            "collection_date": row["collection_date"],
            "accession": row["run_accession"],
            "description": "this study",
        })
with open("references/hbv_metadata.tsv") as handle:
    for row in csv.DictReader(handle, delimiter="\t"):
        metadata.append({
            "id": row["accession"],
            "record_type": "public_reference",
            "genotype": row["genotype"],
            "isolate": row["isolate"],
            "country": row["country"],
            "collection_date": row["collection_date"],
            "accession": row["accession"],
            "description": row["description"],
        })
with open(outdir / "all_hbv_metadata.tsv", "w", newline="") as handle:
    writer = csv.DictWriter(
        handle,
        fieldnames=["id", "record_type", "genotype", "isolate", "country",
                    "collection_date", "accession", "description"],
        delimiter="\t",
    )
    writer.writeheader()
    writer.writerows(metadata)

print(len(records), "sequences and", len(metadata), "metadata rows")
```

**Step 2 — align and build the tree.**

```bash
mafft --auto --reorder results/downstream/all_hbv_sequences.fasta \
  > results/downstream/hbv_alignment.fasta

iqtree2 -s results/downstream/hbv_alignment.fasta \
  -m MFP -B 1000 --alrt 1000 -nt AUTO -redo -quiet \
  --prefix results/downstream/hbv_phylogeny
```

**Step 3 — check the alignment before reading the tree.**

```python
from collections import Counter
from Bio import AlignIO

aln = AlignIO.read("results/downstream/hbv_alignment.fasta", "fasta")
length = aln.get_alignment_length()
gap = n = variable = informative = 0

for i in range(length):
    counts = Counter(aln[:, i].upper())
    gap += counts.get("-", 0)
    n += counts.get("N", 0)
    bases = {base: count for base, count in counts.items() if base not in "-N"}
    if len(bases) > 1:
        variable += 1
        if sum(1 for count in bases.values() if count >= 2) >= 2:
            informative += 1

nseq = len(aln)
print(f"{nseq} sequences, {length} columns")
print(f"{variable} variable, {informative} parsimony-informative")
print(f"{100 * gap / (nseq * length):.3f}% gaps, {100 * n / (nseq * length):.3f}% N")
```

For the committed alignment this prints 15 sequences, 3,221 columns, 845
variable sites, 535 parsimony-informative sites, 0.726% gaps and 3.481% `N`.
If your numbers differ, you are probably reading an older alignment file.

**Step 4 — draw the tree.**

```python
import csv
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from Bio import Phylo

GENOTYPE_COLORS = {
    "A": "#1f77b4", "B": "#ff7f0e", "C": "#d62728", "D": "#2ca02c",
    "E": "#9467bd", "F": "#8c564b", "G": "#e377c2", "H": "#7f7f7f",
}


def read_tsv(path):
    with open(path, newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sample_labels(metadata_path):
    labels = {}
    for row in read_tsv(metadata_path):
        ident = row["id"]
        if row["record_type"] == "study_consensus":
            labels[ident] = f"{row['isolate']} (this study)"
        else:
            year = row["collection_date"][:4] if row["collection_date"][:4].isdigit() else ""
            country = row["country"].replace("_", " ")
            if year:
                labels[ident] = f"{row['accession']} ({country}, {year})"
            elif country and country != "not available":
                labels[ident] = f"{row['accession']} ({country})"
            else:
                labels[ident] = f"{row['accession']} (RefSeq)"
    return labels


def tree_layout(tree):
    x_coords, y_coords = {}, {}
    for index, terminal in enumerate(tree.get_terminals()):
        y_coords[id(terminal)] = index

    def assign(clade, x):
        x_coords[id(clade)] = x
        if clade.is_terminal():
            return
        for child in clade.clades:
            assign(child, x + (child.branch_length or 0.0))
        y_coords[id(clade)] = (y_coords[id(clade.clades[0])] + y_coords[id(clade.clades[-1])]) / 2

    assign(tree.root, 0.0)
    return x_coords, y_coords, max(x_coords.values())


def plot_tree(tree_path, metadata_path, outpath):
    tree = Phylo.read(tree_path, "newick")
    tree.root_at_midpoint()
    tree.ladderize()
    x_coords, y_coords, max_x = tree_layout(tree)
    meta = {row["id"]: row for row in read_tsv(metadata_path)}
    labels = sample_labels(metadata_path)

    fig, ax = plt.subplots(figsize=(11.5, 0.45 * len(tree.get_terminals()) + 2.2))
    parent_map = {}

    def build_parent_map(node):
        for child in node.clades:
            parent_map[id(child)] = node
            build_parent_map(child)

    build_parent_map(tree.root)
    for clade in tree.find_clades(order="postorder"):
        if clade is tree.root:
            continue
        parent = parent_map[id(clade)]
        x0, x1 = x_coords[id(parent)], x_coords[id(clade)]
        y = y_coords[id(clade)]
        descendants = [t.name.split("|")[0] for t in clade.get_terminals()]
        genotypes = {meta.get(ident, {}).get("genotype", "NA") for ident in descendants}
        color = GENOTYPE_COLORS.get(next(iter(genotypes)), "#333333") if len(genotypes) == 1 else "#777777"
        ax.plot([x0, x1], [y, y], color=color, linewidth=1.4)
        if not clade.is_terminal():
            children_y = [y_coords[id(child)] for child in clade.clades]
            ax.plot([x1, x1], [min(children_y), max(children_y)], color=color, linewidth=1.0)
            if clade.name and clade.name != "Root":
                ax.text(x1 + max_x * 0.002, y + 0.12, clade.name, fontsize=6.5, color="#444444", va="bottom")

    for index, terminal in enumerate(tree.get_terminals()):
        ident = terminal.name.split("|")[0]
        genotype = meta.get(ident, {}).get("genotype", "NA")
        ax.text(
            max_x * 1.01, index, labels.get(ident, terminal.name),
            va="center", fontsize=8.2,
            color=GENOTYPE_COLORS.get(genotype, "#333333"),
            fontweight="bold" if meta.get(ident, {}).get("record_type") == "study_consensus" else "normal",
        )

    ax.set_xlim(-max_x * 0.01, max_x * 1.45)
    ax.set_ylim(-0.8, len(tree.get_terminals()) - 0.2)
    ax.set_yticks([])
    ax.set_xlabel("Substitutions per site")
    ax.set_title("HBV whole-genome phylogeny: 5 study samples + 10 public genomes", loc="left", fontsize=11)
    ax.spines[["top", "right", "left"]].set_visible(False)
    scale = 0.02 if max_x > 0.08 else 0.01
    ax.plot([0, scale], [-0.6, -0.6], color="black", linewidth=2)
    ax.text(scale / 2, -0.45, f"{scale:.2f}", ha="center", fontsize=7)
    handles = [
        plt.Line2D([0], [0], color=color, lw=3, label=genotype)
        for genotype, color in GENOTYPE_COLORS.items()
        if any(row["genotype"] == genotype for row in meta.values())
    ]
    ax.legend(handles=handles, title="Genotype", frameon=False, loc="lower right", fontsize=7, title_fontsize=8)
    fig.tight_layout()
    Path(outpath).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(outpath, dpi=300)
    plt.close(fig)


plot_tree(
    "results/downstream/hbv_phylogeny.treefile",
    "results/downstream/all_hbv_metadata.tsv",
    "results/figures/phylogenetic_tree.png",
)
```

The resulting figure is `results/figures/phylogenetic_tree.png`.

The VCF below counts differences from the mapping reference NC_003977.2. For a
genotype A sample, most of those differences are genotype-defining, not
within-sample mutation. A fairer comparison is the closest curated genome:

```python
from pathlib import Path

from Bio import SeqIO
from Bio.Align import PairwiseAligner

aligner = PairwiseAligner()
aligner.mode = "global"
aligner.match_score = 2
aligner.mismatch_score = -1
aligner.open_gap_score = -5
aligner.extend_gap_score = -0.5

public = {
    record.id.split("|")[0]: str(record.seq).upper()
    for record in SeqIO.parse("references/hbv_public_genomes.fasta", "fasta")
}


def identity(query, target):
    alignment = aligner.align(query, target)[0]
    compared = matches = 0
    for x, y in zip(str(alignment[0]), str(alignment[1])):
        if x in "-N" or y in "-N":
            continue
        compared += 1
        matches += x == y
    return matches / compared


for path in sorted(Path("results/viralrecon/variants/bcftools/consensus/bcftools").glob("*.consensus.fa")):
    record = next(SeqIO.parse(path, "fasta"))
    query = str(record.seq).upper()
    best = max(public, key=lambda accession: identity(query, public[accession]))
    print(record.id, best, f"{identity(query, public[best]):.4f}")
```

This prints KJ854710.1 for the three genotype A samples (94.9–95.5% identity)
and NC_003977.2 for the two genotype D samples (98.3–98.5%). The per-region and
per-effect counts in `manifests/mutation_summary.tsv` use the same comparison
and then translate each codon in the S, P, C and X reading frames; the region
coordinates are taken from the NC_003977.2 GenBank annotation.

Read the variants for one sample (change the sample name as needed):

```bash
bcftools query -f '%CHROM\t%POS\t%REF\t%ALT\t%QUAL\t%FILTER\t[%GT\t%DP\t%AD]\n' \
  results/viralrecon/variants/bcftools/HBV_A_B215_2014_norm.vcf.gz > variants_B215.tsv
```

Plot the variants and write a simple HTML report:

```python
import pandas as pd
import matplotlib.pyplot as plt

variants = pd.read_csv(
    "variants_B215.tsv", sep="\t", header=None,
    names=["chrom", "pos", "ref", "alt", "qual", "filter", "gt", "dp", "ad"],
)

variants["pos"].plot.hist(bins=50)
plt.xlabel("Genome position")
plt.ylabel("Variants")
plt.tight_layout()
plt.savefig("results/figures/variants_B215.png", dpi=150)

variants.to_html("results/analysis_summary.html", index=False)
```

## Reference run

The successful end-to-end platform run is preserved in `results/`
(job `75c29039-842d-49cf-b025-19566e03f976`, Vieomics workspace). It contains
the five consensus genomes, VCFs, BCFtools/SAMtools statistics, FastP reports,
the MultiQC report and the Nextflow execution report. The public-genome
phylogeny is in `results/figures/phylogenetic_tree.png`, with the
alignment and tree files under `results/downstream/`. See
`results/README.md` for the exact parameters and output paths.

## Key results from the reference run

The table and bullets below describe the platform reference run. The walkthrough
above reproduces the viralrecon consensus, MAFFT alignment, IQ-TREE phylogeny,
variant table and figures.

| Sample | Genotype | Bowtie2 mapping | Mean depth | Breadth ≥10× | Consensus N | Status |
|---|---|---:|---:|---:|---:|---|
| B215/2014 | A | 84.3% | 40,310× | 99.5% | 0.5% | near-complete |
| B575/2014 | A | 71.2% | 24,944× | 65.1% | 34.9% | partial |
| B3392/2014 | A | 76.8% | 24,431× | 99.5% | 0.5% | near-complete |
| B2719/2015 | D | 99.6% | 48,467× | 100.0% | 0.0% | complete coverage |
| B364/2014 | D | 99.2% | 44,223× | 83.1% | 16.9% | partial |

Mapping, depth and breadth are from the platform viralrecon/Bowtie2 run
(`results/downstream/sample_summary.tsv`). `manifests/mapping_stats.tsv` is a
separate BWA validation run; its `bwa_*` depth and breadth columns should not be
mixed with this table.

- MAFFT alignment: 15 sequences, 3,221 columns, 845 variable sites,
  535 parsimony-informative sites, 0.73% gaps and 3.48% `N`. Thirty-nine
  gap-rich columns form two blocks (2,356–2,361 and 2,863–2,895); no columns
  were trimmed.
- IQ-TREE 2: best model TVM+F+I+G4, 1,000 UFBoot + 1,000 SH-aLRT.
- The three genotype A samples form a clade with KJ854710.1 (100/100). B215 and
  B575 pair, and B3392 branches next.
- The two genotype D samples fall in the D clade with NC_003977.2 and the
  Brazilian D references. The D pair itself has only 28.5/61 support, consistent
  with the missing data in B364/2014.
- The B/C references form a clade (97.4/92); B and C are each monophyletic
  (100/100). E and F provide outgroup context.
- VCF calls relative to NC_003977.2: 1,942 unique SNP positions across the five
  samples (660, 571, 481, 123 and 107 per sample); the VCFs contain SNP records
  only (no indels). `results/downstream/variant_summary.tsv` counts each record
  once per overlapping ORF, so its S/P/C/X columns sum to more than 1,942.
- Compared with the closest curated genome instead, there are 633
  region-annotated nucleotide rows and 593 amino-acid rows across the five
  samples (473 unique nucleotide positions before counting overlapping ORFs),
  plus six deletion candidates. Closest-genome identity is 94.9–95.5% for the A
  samples and 98.3–98.5% for the D samples. The full tables are
  `manifests/nucleotide_variants.tsv` and `manifests/amino_acid_variants.tsv`.

## Important caveats

- **This is a demonstration, not an epidemiological or clinical study.** Five
  samples and ten references cannot support transmission, geographic-origin or
  resistance claims.
- B575/2014 and B364/2014 are **partial genomes**. Their low-coverage blocks are
  reported and masked as `N`; they are not treated as complete genomes. The three
  genotype A samples also carry a short 16–17 bp `N` run at 2,856–2,872, which is
  a zero-depth/deletion region rather than a complete assembly.
- The consensus is **reference-guided and fixed to the 3,182 bp NC_003977.2
  coordinate frame**. Indels are not applied; deletion candidates are reported
  separately in `manifests/indel_candidates.tsv`. An `N` is not a gap, and the
  consensus length is not an assembly length.
- The 15-sequence alignment has two gap-rich blocks (2,356–2,361 and
  2,863–2,895). They are retained rather than trimmed, so phylogenetic signal
  around those blocks is alignment-uncertain.
- The PhiPack screen was run on the earlier alignment (533 informative sites;
  the committed alignment has 535) and the panel spans genotypes A–F. PHI and
  NSS are below the 1,000-permutation resolution and Max χ² is p = 0.028. This
  is a signal to investigate, not a recombination breakpoint claim. See
  `manifests/recombination_screen.md`.
- The public panel is a curated context set, not a representative global sample.
- Raw variant counts are not a mutation rate, and no clinical HBV mutation
  database was queried. No variant is labelled drug resistant or immune escape.

## Environment and container note

The upstream `nf-core/viralrecon` step now runs as an OmicsLab platform job on
public GreenNode compute with the public GitHub credential. The local pixi
environment contains the downstream tools (BWA, SAMtools, BCFtools, MAFFT,
IQ-TREE 2, PhiPack, Python, pandas, matplotlib), so the interactive analysis
does not depend on a local Docker/Apptainer runtime.

The platform job is pinned to the `nf-core/viralrecon` `dev` commit
`31b9515f6e166542ca60358931351aa0f9a72b8a`, which is compatible with the
platform Nextflow 26 runtime. Viralrecon 2.6.0 cannot be used there because its
legacy `check_max()` config helper fails on Nextflow 26.

## Software versions

Main tools: fastp 1.4.0, Bowtie2 2.5.5, SAMtools 1.24, BCFtools 1.23.1,
bedtools 2.31.1, MAFFT 7.526, IQ-TREE 2.4.0, Python 3.13, Biopython 1.88,
pysam 0.24.1. The platform job used nf-core/viralrecon v3.1.0dev and Nextflow
26.04.6.

## Citations

- nf-core/viralrecon: DOI 10.5281/zenodo.3901628
- Nextflow: DOI 10.1038/nbt.3820
- IQ-TREE 2: DOI 10.1093/molbev/msaa015
- MAFFT: DOI 10.1093/molbev/mst010
- PhiPack: DOI 10.1093/molbev/msj092
- GenBank accessions are listed in `references/hbv_metadata.tsv` and above.
