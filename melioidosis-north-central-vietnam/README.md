# Melioidosis in North Central Vietnam — reproduction

Reproduction of the public-data analysis in:

> Norris MH, Au La TH, Metrailer MC, et al. (2026). Expanding the molecular
> epidemiology of melioidosis in North Central Vietnam. *PLOS Neglected Tropical
> Diseases* 20(2): e0013945.
> [doi:10.1371/journal.pntd.0013945](https://doi.org/10.1371/journal.pntd.0013945)

This is an **isolate whole-genome sequencing** study, not a metagenomics study.
The matching pipeline is `nf-core/bacass` (FastP → Unicycler → Prokka), followed
by MLST/cgMLST, whole-genome SNP phylogeny, and pan-genome analysis.

## Data

- New genomes: 47 *Burkholderia pseudomallei* isolates in SRA
  [`PRJNA1180080`](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1180080)
  (35 clinical, 10 soil, 2 animal).
- Comparative set: 1,468 genomes total, including the 47 new isolates. The
  paper downloaded these as raw SRA reads and assembled them with bacass.
- The paper's S1 Table contains SRA accessions and metadata only; there is no
  FASTA or assembly accession column.

The 47-run manifest is [`ids.csv`](ids.csv); the one-run test manifest is
[`ids.single.csv`](ids.single.csv).

## Current status

- [x] Paper and data availability reviewed.
- [x] S1 Table inspected; 47 new runs confirmed.
- [x] One-sample fetchngs test defined: `SRR31184429` (`Bp52_TY01`).
- [ ] One-sample fetchngs job run on OmicsLab and output verified.
- [ ] 47-sample bacass run.
- [ ] Comparative 1,468-genome analysis.

## Environment

The solution uses the same pixi-managed Nextflow/Apptainer environment as
`ndm-truncation-reanalysis/`:

```bash
pixi install
pixi run fetchngs-single
```

`fetchngs-single` downloads the one test run with `sratools`; `fetchngs`
downloads all 47 runs.

## Reproduction plan

See [`docs/reproduction-plan.md`](docs/reproduction-plan.md) for the phased
plan, bacass settings, resource sizing, and cost estimate.

## Proposed workspace layout

```text
s3://vieomics-prod/data/datasets/gianglabs/47-samples/
├── fastq/                 # 47 runs, one directory per SRR accession
└── samplesheets/
    └── PRJNA1180080.tsv   # 47-row bacass samplesheet
```

The final prefix can be changed; it must match the paths written into the
bacass samplesheet.
