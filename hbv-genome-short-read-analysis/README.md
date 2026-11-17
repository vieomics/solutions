# HBV whole-genome short-read analysis

Reproducible analysis of five Illumina HBV whole-genome sequencing runs from
NCBI BioProject [PRJNA659786](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA659786)
plus ten curated complete GenBank genomes. The deliverable includes a
stock `nf-core/viralrecon` run, a circular-genome HBV branch, MAFFT alignment,
IQ-TREE 2 phylogeny, recombination screening, overlapping-ORF variant
annotation, figures and a technical blog.

The long-form write-up is in **[docs/blog.md](docs/blog.md)**. The integrated
HTML report from the actual run is `results/analysis_summary.html`.

## What is in this solution

```text
hbv-genome-short-read-analysis/
├── README.md
├── pixi.toml / pixi.lock          # pinned environment (two envs)
├── samplesheet.csv                # generated; absolute paths
├── metadata/
│   ├── selected_samples.tsv       # five runs and ENA/SRA metadata
│   ├── ena_run_metadata.tsv       # project metadata snapshot
│   └── samplesheet.csv            # original nf-core/fetchngs-style sheet
├── references/
│   ├── hbv_reference.fasta        # NC_003977.2 (genotype D, strain ayw)
│   ├── hbv_reference.extended.fasta
│   ├── hbv_public_genomes.fasta   # 10 public genomes, origin-normalised
│   ├── hbv_metadata.tsv           # accessions, genotype, country, date, QC
│   ├── reference_selection.md
│   ├── fetch_manifest.json
│   └── genbank/                   # cached GenBank flat files
├── bin/                           # download, reference, circular, figure, report scripts
├── workflow/
│   ├── main.nf                    # DSL2 downstream workflow
│   ├── nextflow.config
│   └── README.md
├── conf/
│   └── viralrecon.config          # local resources + custom genome entry
├── results/                       # full run outputs (git-ignored)
├── docs/
│   ├── blog.md
│   └── figures/                   # figures used in the blog
└── manifests/                     # small committed summary tables/manifest
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

Raw FASTQ files are not committed. They are downloaded from OmicsLab storage
with `bin/download_fastq.sh`, which verifies every file against its ENA MD5;
`bin/verify_fastq.sh` can re-check gzip integrity and MD5 at any time. The five
runs are already staged in the workspace, so `nf-core/fetchngs` is not required
for this solution. If an independent ENA/SRA re-download is wanted, the five SRR
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

Install pixi and the two environments:

```bash
pixi install
```

Download the five FASTQ pairs (requires the OmicsLab CLI and the
`datasets/gianglabs/PRJNA659786` storage prefix):

```bash
omx cd datasets/gianglabs/PRJNA659786   # if not already there
bash bin/download_fastq.sh
bash bin/verify_fastq.sh
```

Build the reference panel and samplesheet:

```bash
pixi run python bin/fetch_public_references.py --outdir references
pixi run python bin/make_samplesheet.py
pixi run python bin/make_extended_reference.py
```

Run the stock nf-core/viralrecon 2.6.0 pipeline with the local pixi tools:

```bash
pixi run -e viralrecon nextflow run nf-core/viralrecon -r 2.6.0 \
  -c conf/viralrecon.config \
  --input samplesheet.csv --outdir results/viralrecon \
  --platform illumina --protocol metagenomic --genome hbv \
  --skip_assembly --skip_kraken2 --skip_pangolin --skip_nextclade \
  --skip_snpeff --skip_variants_quast --skip_variants_long_table \
  --skip_picard_metrics --skip_mosdepth --skip_consensus_plots \
  --skip_asciigenome -resume
```

Run the HBV-specific downstream workflow:

```bash
pixi run nextflow run workflow/main.nf -profile local -resume
```

Regenerate the report/manifest after the workflow:

```bash
pixi run python bin/combine_mapping_stats.py
pixi run python bin/make_figures.py
pixi run python bin/make_report.py
pixi run bash bin/software_versions.sh
pixi run python bin/make_manifest.py
```

The workflow writes to `results_nf/` by default; the committed run used
`--outdir results`. See `workflow/README.md` for details.

## Why there are two mapping branches

`nf-core/viralrecon` uses Bowtie2 against a linear reference and is excellent
for QC, mapping, BCFtools variant calling and consensus generation. A linear
reference still loses reads that cross the arbitrary HBV origin. The downstream
workflow therefore maps the same trimmed reads with BWA-MEM to an
origin-extended reference (NC_003977.2 plus the first 500 bp duplicated at the
3′ end), projects every position modulo 3,182 bp, and uses that circular pileup
to:

- report depth and breadth of coverage over the true circular genome;
- count reads spanning the origin;
- patch the viralrecon consensus at boundary positions that were `N` because
  of the linear representation.

## Key results from the committed run

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
  D references (D sample pair support 30/55, limited by missing data).
- B/C references form a well-supported clade (98.6/92).
- PhiPack reports a recombination signal (PHI p=0, Max Chi² p=0.034); region-
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

The workspace used for the committed run has no usable Docker/Apptainer runtime
(user namespaces are blocked), so the pipeline was executed with pinned pixi
environments. `pixi.lock` records the exact tool versions. The nf-core step is
pinned at viralrecon 2.6.0 and uses Nextflow 24.10.6; the downstream workflow
uses Nextflow 26.10.6. The `workflow/nextflow.config` has a placeholder
`apptainer` profile; only process-level container directives need to be added on
a host with Apptainer.

`stageInMode = 'copy'` is set in both Nextflow configs so that a process can
never truncate the original FASTQ through a staged symlink.

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
