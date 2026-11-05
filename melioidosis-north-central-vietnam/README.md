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

## Download on Google Colab

Use [`bin/download_ena_fastq.sh`](bin/download_ena_fastq.sh). It reads the ENA
run report, downloads paired FASTQs with `aria2c` (or `wget`), verifies MD5s,
and writes a bacass samplesheet.

In a Colab bash cell:

```bash
apt-get -qq update
apt-get -qq install -y aria2

# One-run test
OUTDIR=/content/data/PRJNA1180080 \
  bash download_ena_fastq.sh SRR31184429
```

All 47 runs:

```bash
OUTDIR=/content/data/PRJNA1180080 JOBS=8 \
  bash download_ena_fastq.sh
```

Outputs:

```text
/content/data/PRJNA1180080/
├── fastq/*.fastq.gz
├── metadata/PRJNA1180080.ena.tsv
├── metadata/PRJNA1180080.fastq_urls.txt
├── metadata/PRJNA1180080.md5
└── PRJNA1180080.bacass.tsv
```

If `https://ftp.sra.ebi.ac.uk` is blocked in Colab, retry with
`SCHEME=ftp`. To use paper isolate names instead of SRR accessions, set
`MAPPING_TSV` to a two-column TSV (`run_accession`, `isolate_name`).

## Current status

- [x] Paper and data availability reviewed.
- [x] S1 Table inspected; 47 new runs confirmed.
- [x] One-sample fetchngs test defined: `SRR31184429` (`Bp52_TY01`).
- [x] One-sample input uploaded to workspace storage.
- [x] One-sample fetchngs manifest uploaded to workspace storage.
- [ ] One-sample fetchngs job launched on OmicsLab and output verified.
- [ ] 47-sample bacass run.
- [ ] Comparative 1,468-genome analysis.

The manifest is ready at:

```text
analysis/fetchngs/SRR31184429.omxa.json
```

The Studio credential broker blocks job launches from this shell, so the job
must be triggered from the OmicsLab platform UI (or from a terminal with job
launch permission). The manifest already points at:

```text
input:  s3://vieomics-prod/data/datasets/gianglabs/47-samples/ids/SRR31184429.csv
output: s3://vieomics-prod/data/datasets/gianglabs/47-samples/fetchngs-test/$job_id
```

## Environment

The solution uses the same pixi-managed Nextflow/Apptainer environment as
`ndm-truncation-reanalysis/`:

```bash
pixi install
pixi run fetchngs-single
```

`fetchngs-single` downloads the one test run with `sratools`; `fetchngs`
downloads all 47 runs.

The platform manifest template is
[`manifests/fetchngs.single.omxa.json`](manifests/fetchngs.single.omxa.json).
Replace `__VERSIONING_ID__` and `__BUCKET__`, then upload and launch it from a
terminal with job-launch permission:

```bash
omx ws analysis config upload manifests/fetchngs.single.omxa.json \
  --key analysis/fetchngs/SRR31184429.omxa.json \
  -w "$WORKSPACE"

omx ws analysis config launch analysis/fetchngs/SRR31184429.omxa.json \
  -w "$WORKSPACE" \
  -n fetchngs-SRR31184429-test \
  --cpu 4 --memory 8 --disk 100 --time 1h
```

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
