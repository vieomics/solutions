# Bacterial genome assembly and NDM truncation investigation

Reproducible assembly and read-level reanalysis of the five bacterial isolates
with a discordant `blaNDM` PCR / ceftazidime-avibactam phenotype reported by
Dung et al. 2025
(*Ann Clin Microbiol Antimicrob*, doi:10.1186/s12941-025-00818-3).

This is one self-contained solution in the
[vieomics/solutions](../README.md) repository.

- Raw data: ENA project [PRJEB86571](https://www.ebi.ac.uk/ena/browser/view/PRJEB86571)
- Branch: `main`

| Run | Isolate | Reported species |
|-----|---------|------------------|
| ERR14693661 | 03-A-063 | *Klebsiella pneumoniae* |
| ERR14693662 | 03-A-038 | *Klebsiella pneumoniae* |
| ERR14693663 | 24-A-028 | *Klebsiella pneumoniae* |
| ERR14693664 | 11-A-427 | *Klebsiella pneumoniae* |
| ERR14693665 | 021-A-244 | *Pseudomonas aeruginosa* (ENA `scientific_name` field is mislabelled as *K. pneumoniae*) |

---

## Setup

Everything (Nextflow, Apptainer) is managed by [pixi](https://pixi.sh).
You do **not** need to install Nextflow, Java, or a container engine by hand.

### 1. Install pixi (one time)

```bash
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"   # or restart your shell
pixi --version
```

### 2. Clone and enter the project

```bash
git clone git@github.com:vieomics/solutions.git
cd solutions/bacteria-genome-assembly
```

### 3. Create the environment

```bash
pixi install
```

This reads `pixi.toml`, resolves dependencies and writes `pixi.lock`.
It installs into `.pixi/` (git-ignored) and gives you:

- `nextflow` — pinned by the lock file
- `apptainer` — pinned by the lock file

Verify:

```bash
pixi run nextflow -version
pixi run apptainer --version
```

### 4. Container engine notes

- **Apptainer (default here):** runs rootless via unprivileged user namespaces.
  Requires `kernel.unprivileged_userns_clone=1` (check with
  `cat /proc/sys/kernel/unprivileged_userns_clone`).
- **Docker fallback:** if Apptainer cannot run on a host, use `-profile docker`
  instead of `-profile apptainer`.
- **Registry:** the pipelines pull SIF images from `quay.io/nf-core/...`.
  If your network blocks Quay, add a registry override:

  ```bash
  export NXF_CONTAINER_REGISTRY=docker.io
  # or point Apptainer at a local mirror:
  export NXF_APPTAINER_CACHEDIR=/path/to/shared/sif-cache
  ```

### Resource policy

`conf/resources.config` enforces a **2 GB RAM per CPU** ratio and sets
`process_medium` to **16:32** (host: 79 CPUs / 256 GB):

| label | CPUs | RAM |
|---|---|---|
| default | 1 | 2 GB |
| process_single | 1 | 2 GB |
| process_low | 2 | 4 GB |
| process_medium | 16 | 32 GB |
| process_high | 16 | 32 GB |

It is passed with `-c`, so it overrides the nf-core defaults (which use
1 CPU : 6 GB for `process_single`).

### 5. Executor notes

- On a machine with SLURM, Nextflow will pick up the local configuration if one
  exists (`~/.nextflow/config`). This repo's runs here used `executor > slurm`.
- On a plain workstation, force local execution:

  ```bash
  pixi run nextflow run ... -process.executor local
  ```

---

## Run the pipeline

### Fetch reads (download + MD5 verification)

```bash
pixi run fetchngs
# equivalent to:
pixi run nextflow run nf-core/fetchngs -r 1.13.0 -profile apptainer \
    -c conf/fetchngs.config -c conf/resources.config \
    --download_method sratools \
    --input ids.csv --outdir results/fetchngs -resume
```

> **Why `sratools`?** ENA's HTTP/FTP mirror (`ftp.sra.ebi.ac.uk`) throttled to
> <1 MB/s and stalled on the compute nodes, while the NCBI SRA mirror (S3)
> measured ~10 MB/s. `sratools` downloads the same runs via NCBI
> (`prefetch` + `fasterq-dump`) and still verifies the FASTQs.
```

### Convert the samplesheet for bacass

```bash
python3 bin/fetchngs_to_bacass.py \
    --input results/fetchngs/samplesheet/samplesheet.csv \
    --output bacass_samplesheet.tsv
```

### Assemble and annotate

```bash
pixi run bacass
# equivalent to:
pixi run nextflow run nf-core/bacass -r 2.6.1 -profile apptainer \
    -c conf/resources.config \
    --input bacass_samplesheet.tsv --outdir results/bacass \
    --assembly_type short --assembler unicycler \
    --annotation_tool prokka --skip_kraken2 -resume
```

Raw reads and intermediate files land in `results/` and `work/` — both are
git-ignored.

### Alternative: one OmicsLab job per sample

The commands above run all five samples in a single Nextflow session. If you
would rather not keep one machine alive for the whole batch, submit one
`nf-core/bacass` analysis job per sample on the OmicsLab platform. The pipeline,
tag, pinned commit and resources stay identical; only `params.input` and the job
name change.

This repository ships one-row samplesheets for the five ENA runs under
`samplesheets/omicslab/`. The full walkthrough is in
[`docs/omicslab-multijob.md`](docs/omicslab-multijob.md).

Quick start, after `omx auth login` and with a completed bacass job to copy:

```bash
export WORKSPACE=<omicslab-workspace-id>
export SOURCE_JOB=<completed-bacass-job-id>

bin/submit_bacass_jobs.sh \
  ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665
```

Each job is named `bacass-<sample>` and writes to its own
`s3://<workspace-bucket>/data/bacass/<job-id>` prefix.

---

## Repository layout

```
ids.csv                      # ENA run accessions (PRJEB86571)
bacass_samplesheet.tsv       # combined samplesheet (local fetchngs paths)
samplesheets/omicslab/       # one-row bacass sheets for the five ENA runs
analysis/                    # read-level blaNDM audit pipeline
bin/                         # converters, plotting and submission helpers
conf/                        # Nextflow configs
docs/blog.md                 # findings write-up
docs/omicslab-multijob.md    # per-sample OmicsLab job walkthrough
params/                      # nf-core/bacass params file
pixi.toml / pixi.lock        # environment (Nextflow + Apptainer)
results/                     # pipeline outputs (untracked)
work/                        # Nextflow work directory (untracked)
logs/                        # run logs (untracked)
```

## Investigation notes

Read-level audit of the reported `blaNDM` truncations, distinguishing:

- **H1** true deletion
- **H2** assembly artifact (repeat collapse / coverage dropout)
- **H3** mobile remnant or second (silent) copy
- **H4** intact but silenced allele (promoter disruption)

**Findings write-up: [`docs/blog.md`](docs/blog.md)** — read-level reanalysis of all
5 isolates, IS26-mediated junction mechanism, ST16 clonal context, and the
diagnostic implications. Figures in `docs/figures/`.

Follow-up: public `blaNDM` junction recurrence and co-selection mining.
