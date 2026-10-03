# vieomics/solutions — NDM truncation investigation

Reproducible reanalysis of the five bacterial isolates with a discordant `blaNDM`
PCR / ceftazidime-avibactam phenotype reported by Dung et al. 2025
(*Ann Clin Microbiol Antimicrob*, doi:10.1186/s12941-025-00818-3).

- Raw data: ENA project [PRJEB86571](https://www.ebi.ac.uk/ena/browser/view/PRJEB86571)
- Branch: `topic/ndm-truncation`

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
cd solutions
git checkout topic/ndm-truncation
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

---

## Repository layout

```
ids.csv                      # ENA run accessions (PRJEB86571)
bin/fetchngs_to_bacass.py    # samplesheet converter
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

Follow-up: public `blaNDM` junction recurrence and co-selection mining.
