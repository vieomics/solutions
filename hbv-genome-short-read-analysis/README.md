# HBV whole-genome short-read analysis

Reproducible analysis of five Illumina HBV whole-genome sequencing runs from
NCBI BioProject [PRJNA659786](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA659786)
plus ten curated complete GenBank genomes. The deliverable includes a
stock `nf-core/viralrecon` run, MAFFT alignment, IQ-TREE 2 phylogeny,
recombination screening, variant tables, figures and a technical blog.

The long-form write-up is in **[docs/blog.md](docs/blog.md)**. The integrated
HTML report from the actual run is `results/analysis_summary.html`.

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
├── results/                       # full run outputs (git-ignored)
├── reference_results/             # successful platform run (consensus, variants, MultiQC)
├── docs/
│   ├── blog.md
│   └── figures/                   # figures used in the blog
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

Use the OmicsLab SDK shell for the platform CLI (run this from your platform
checkout):

```bash
pixi shell --manifest-path pixi.toml -e sdk
```

From this solution directory:

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

If you prefer a local copy of the public config, download and re-upload the
three small files into your workspace, then point the manifest paths at your
workspace. The public copies remain the canonical templates.

If the public prefix does not yet contain those small files, stage them once as
an administrator in the public workspace
(`c669cc81-d096-4679-a9a2-03329167b71f`):

```bash
PUBLIC_WORKSPACE='c669cc81-d096-4679-a9a2-03329167b71f'
omx upload metadata/samplesheet.platform.csv \
  analysis/PRJNA659786/samplesheet.csv -w "$PUBLIC_WORKSPACE" -y
omx upload conf/viralrecon.platform.config \
  analysis/PRJNA659786/viralrecon.config -w "$PUBLIC_WORKSPACE" -y
omx upload references/hbv_reference.fasta \
  analysis/PRJNA659786/references/hbv_reference.fasta -w "$PUBLIC_WORKSPACE" -y
```

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

Combine the five consensus sequences with the public reference panel:

```bash
cat results/viralrecon/variants/bcftools/consensus/bcftools/*.consensus.fa \
    references/hbv_public_genomes.fasta > comparative/all_hbv_sequences.fasta
```

Align and build the tree:

```bash
mafft --auto --reorder comparative/all_hbv_sequences.fasta > alignment/hbv_alignment.fasta
iqtree2 -s alignment/hbv_alignment.fasta -m MFP -B 1000 --alrt 1000 -nt AUTO --prefix results/phylogeny/hbv_phylogeny -redo
```

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
plt.savefig("docs/figures/variants_B215.png", dpi=150)

variants.to_html("results/analysis_summary.html", index=False)
```

## Reference run

The successful end-to-end platform run is preserved in `reference_results/`
(job `75c29039-842d-49cf-b025-19566e03f976`, Vieomics workspace). It contains
the five consensus genomes, VCFs, BCFtools/SAMtools statistics, FastP reports,
the MultiQC report and the Nextflow execution report. See
`reference_results/README.md` for the exact parameters and output paths.

## Key results from the committed run

The table and bullets below describe the committed run, which used the earlier
custom circular/annotation code. The walkthrough above reproduces the
viralrecon consensus, MAFFT alignment, IQ-TREE phylogeny and variant table.

| Sample | Genotype | BWA mapping | Mean depth | Breadth ≥10× | Consensus N | Status |
|---|---|---:|---:|---:|---:|---|
| B215/2014 | A | 89.3% | 40,107× | 99.0% | 0.5% | near-complete |
| B575/2014 | A | 76.8% | 24,824× | 63.8% | 34.8% | partial |
| B3392/2014 | A | 86.3% | 25,810× | 97.9% | 0.5% | near-complete |
| B2719/2015 | D | 99.8% | 49,126× | 100.0% | 0.0% | complete coverage |
| B364/2014 | D | 99.6% | 44,767× | 83.2% | 16.8% | partial |

- MAFFT alignment: 15 sequences, 3,221 columns, 842 variable sites, 533
  parsimony-informative sites, 0.73% gaps.
- IQ-TREE 2: best model TVM+F+I+G4, 1,000 UFBoot + 1,000 SH-aLRT.
- The three genotype A samples form a clade with KJ854710.1 (100/100).
- The two genotype D samples fall in the D clade with NC_003977.2 and Brazilian
  D references (D sample pair support 28.8/56, limited by missing data).
- B/C references form a well-supported clade (97.6/92).
- PhiPack reports a recombination signal (PHI p=0, Max Chi² p=0.028); region-
  specific S and P trees are provided, but no breakpoint is claimed.
- Variant tables: 675 nucleotide rows and 625 amino-acid rows across five
  samples (overlapping ORFs are annotated independently).

## Important caveats

- **This is a demonstration, not an epidemiological or clinical study.** Five
  samples and ten references cannot support transmission, geographic-origin or
  resistance claims.
- B575/2014 and B364/2014 are **partial genomes**. Their low-coverage blocks are
  reported and masked as `N`; they are not treated as complete genomes.
- The shared P W592* stop in the A samples is a high-confidence nucleotide call
  but its biological meaning is unresolved. It is not labelled a resistance or
  immune-escape mutation.
- Recombination tests can be inflated by missing data. The recombination result
  is reported as a limitation, not a breakpoint claim.
- The public panel is a curated context set, not a representative global sample.
- No clinical HBV mutation database was queried; effects are limited to
  synonymous/nonsynonymous/stop/uncertain classes.

## Environment and container note

The upstream `nf-core/viralrecon` step now runs as an OmicsLab platform job on
public GreenNode compute with the public GitHub credential. The local pixi
environment only contains the downstream tools (BWA, SAMtools, BCFtools, MAFFT,
IQ-TREE, PhiPack, Python), so the interactive analysis does not depend on a
local Docker/Apptainer runtime.

The platform job is pinned to the `nf-core/viralrecon` `dev` commit
`31b9515f6e166542ca60358931351aa0f9a72b8a`, which is compatible with the
platform Nextflow 26 runtime. Viralrecon 2.6.0 cannot be used there because its
legacy `check_max()` config helper fails on Nextflow 26.

## Software versions

See `manifests/software_versions.tsv`. Main tools: fastp 1.0.1 (viralrecon env)
and 1.4.0 (downstream), Bowtie2 2.5.4, BWA 0.7.19, SAMtools 1.21/1.25,
BCFtools 1.22/1.25, MAFFT 7.526, IQ-TREE 2.4.0, PhiPack 1.1, MultiQC 1.31/1.35,
Python 3.13, Biopython 1.88, pysam 0.24.1.

## Blog and citations

- [Technical blog](docs/blog.md)
- nf-core/viralrecon: DOI 10.5281/zenodo.3901628
- Nextflow: DOI 10.1038/nbt.3820
- IQ-TREE 2: DOI 10.1093/molbev/msaa015
- MAFFT: DOI 10.1093/molbev/mst010
- PhiPack: DOI 10.1093/molbev/msj092
- GenBank accessions are listed in `references/hbv_metadata.tsv` and above.
