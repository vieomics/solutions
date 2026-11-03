# Five samples, five jobs: scaling nf-core/bacass on OmicsLab

*How to turn a one-machine batch into per-sample analysis jobs with the `omx`
SDK.*

---

## The default: one machine, one batch

The usual way to run a small reanalysis is to start one VM, install Nextflow,
point `--input` at a five-row samplesheet, and wait. It is simple and it works.

But it has a few sharp edges:

- all five samples share one lifecycle and one log stream;
- a failure in one sample can take down the whole batch;
- you cannot give one difficult sample more CPU without also paying for the
  other four;
- the VM sits idle between pipeline steps;
- reproducing one sample means re-running the batch, or hand-editing the
  samplesheet.

On OmicsLab, the unit of work is an **analysis job**, not a machine. The
platform provisions the VM, mounts the workspace storage, runs the pipeline,
streams the logs and publishes the output. That makes a different shape
possible: **one job per sample**.

Same pipeline, same tag, same pinned commit, same resources. Only two things
change:

1. `params.input` points at a one-row samplesheet;
2. the job name includes the sample.

The rest of this post is the exact workflow for the five `PRJEB86571` isolates
with `nf-core/bacass` 2.6.1.

---

## What you need

- the `omx` CLI / SDK (this walkthrough uses `omicslab v2.6.0`);
- an OmicsLab account with access to the target workspace;
- a known-good `nf-core/bacass` job to copy, or a launch manifest;
- one-row bacass samplesheets for each run.

Check the client and context first:

```bash
which omx
omx --version
omx whoami
omx env
```

Set the workspace once for the rest of the session:

```bash
export WORKSPACE=<workspace-id>
omx ws get "$WORKSPACE"
```

`omx env` also shows the workspace that is currently active. Every command
below accepts `-w "$WORKSPACE"`, so there is no ambiguity if you switch
workspaces later.

---

## Step 1: get one-row samplesheets

`nf-core/bacass` expects a TSV with these columns:

```text
ID	R1	R2	LongFastQ	Fast5	GenomeSize
```

For the `PRJEB86571` example, the public Omicslab resource workspace already has
one sheet per run:

```bash
omx ls s3://omicslab/data/datasets/gianglabs/PRJEB86571/
```

```text
bacass_PRJEB86571_ERR14693661.tsv
bacass_PRJEB86571_ERR14693662.tsv
bacass_PRJEB86571_ERR14693663.tsv
bacass_PRJEB86571_ERR14693664.tsv
bacass_PRJEB86571_ERR14693665.tsv
```

This repository keeps the same five sheets under `samplesheets/omicslab/`, each
containing a single row. One sheet, one job:

```text
ID	R1	R2	LongFastQ	Fast5	GenomeSize
ERR14693661	s3://omicslab/data/datasets/gianglabs/PRJEB86571/ERX14095152_ERR14693661_1.fastq.gz	s3://omicslab/data/datasets/gianglabs/PRJEB86571/ERX14095152_ERR14693661_2.fastq.gz	NA	NA	NA
```

If you start from a combined sheet, split it:

```bash
python3 bin/split_bacass_samplesheet.py \
    --input bacass_samplesheet.tsv \
    --outdir samplesheets/local \
    --sample-regex '(ERR[0-9]+)'
```

The `--sample-regex` is optional. By default the script names each output file
from the `ID` column. The regex is useful when `ID` is an ENA experiment
accession (`ERX...`) but you want the run accession (`ERR...`) in filenames and
job names.

---

## Step 2: pick a known-good source job

List the bacass history, newest first:

```bash
omx ws analysis list -w "$WORKSPACE" \
    --history --search bacass \
    --sort created_at --desc
```

Then inspect the job you want to copy:

```bash
omx ws analysis get <source-job-id> -w "$WORKSPACE"
```

Verify four things:

- **tool and tag** — e.g. `https://github.com/nf-core/bacass.git`, `2.6.1`;
- **pinned commit** — the rerun keeps the exact commit;
- **resources** — in this example 16 CPU, 32 GB RAM, 100 GB disk, 1 hour;
- **output prefix** — it must contain `$job_id`, e.g.
  `s3://vieomics-prod/data/bacass/$job_id`.

The table from `get` does not show every param. If you need the resolved launch
manifest, ask the SDK directly:

```python
from omicslab import Client

client = Client()
manifest = client.jobs.get_analysis_manifest(
    "<workspace-id>", "<source-job-id>"
)
print(manifest["params"]["input"])
print(manifest["params"]["outdir"])
```

That manifest is what `rerun` copies. Keeping it as the source of truth is the
whole trick: the pipeline version and resource shape cannot drift between
samples.

---

## Step 3: upload the one-row sheets

Upload the sheets to the workspace storage that the job can read:

```bash
for sample in ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665; do
    omx upload "samplesheets/omicslab/$sample.tsv" \
        "s3://vieomics-prod/data/bacass/samplesheets/$sample.tsv" -y
done
```

Verify:

```bash
omx ls s3://vieomics-prod/data/bacass/samplesheets
```

---

## Step 4: submit the first job

```bash
omx ws analysis rerun "$SOURCE_JOB" \
    -w "$WORKSPACE" \
    -n bacass-ERR14693661 \
    -p input=s3://vieomics-prod/data/bacass/samplesheets/ERR14693661.tsv \
    --json
```

Why `rerun` instead of `launch`?

- it copies the resolved launch manifest, including tool, tag, commit,
  versioning, config and resource workspace;
- only the flags you pass are changed;
- params are merged per top-level key, so the other 60+ bacass params are
  untouched;
- the response includes `changed_parameters`, which is a built-in audit of the
  input swap.

In the response you will see something like:

```json
"changed_parameters": [
  {
    "field": "params.input",
    "old": "s3://vieomics-prod/data/bacass_test_full_short_read.tsv",
    "new": "s3://vieomics-prod/data/bacass/samplesheets/ERR14693661.tsv"
  }
]
```

---

## Step 5: submit the rest

```bash
for sample in ERR14693662 ERR14693663 ERR14693664 ERR14693665; do
    omx ws analysis rerun "$SOURCE_JOB" \
        -w "$WORKSPACE" \
        -n "bacass-$sample" \
        -p "input=s3://vieomics-prod/data/bacass/samplesheets/$sample.tsv" \
        --json
done
```

The naming convention matters more than it looks. `bacass-<run-accession>`
means the job list, the log URL and the output folder all map back to the
sample without opening a spreadsheet.

The helper script wraps upload and submit:

```bash
WORKSPACE=<workspace-id> SOURCE_JOB=<source-job-id> \
    bin/submit_bacass_jobs.sh \
    ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665
```

Use `DRY_RUN=1` to print the commands first:

```bash
WORKSPACE=ws SOURCE_JOB=job DRY_RUN=1 \
    bin/submit_bacass_jobs.sh ERR14693661
```

---

## Step 6: monitor and retry

```bash
omx ws analysis list -w "$WORKSPACE" --active
omx ws analysis logs <job-id> -w "$WORKSPACE"
```

Jobs move through:

```text
submitting -> submitted -> pending -> running -> completed
                                             -> failed
```

`omx ws analysis logs` streams live output for a running job; press `Ctrl+C` to
disconnect without stopping the job.

If one job fails, rerun **that job**:

```bash
omx ws analysis rerun <failed-job-id> \
    -w "$WORKSPACE" \
    -n bacass-ERR14693661-r2 \
    --json
```

With no `-p` flags, the rerun is an exact copy. This is the main operational
win over a single batch: a bad sample gets a new VM and a new attempt without
touching the other four jobs.

---

## What this looked like on the five isolates

| Run | Isolate | Species | Job name |
|---|---|---|---|
| ERR14693661 | 03-A-063 | *K. pneumoniae* | `bacass-ERR14693661` |
| ERR14693662 | 03-A-038 | *K. pneumoniae* | `bacass-ERR14693662` |
| ERR14693663 | 24-A-028 | *K. pneumoniae* | `bacass-ERR14693663` |
| ERR14693664 | 11-A-427 | *K. pneumoniae* | `bacass-ERR14693664` |
| ERR14693665 | 021-A-244 | *P. aeruginosa* | `bacass-ERR14693665` |

The job-name column shows the convention used for the multi-job run. The source
job in our workspace was `omicslab-ijm4jx` (bacass 2.6.1, commit `5ed7c2dd…`),
which had already processed ERR14693665, so that sample was not resubmitted. We
then submitted the remaining four as separate jobs.

Two of the four first attempts failed before Nextflow started:

```text
Cloud VM setup timed out: SSH command exceeded 289.851s
Cloud VM setup timed out: bootstrap exceeded the 300s total deadline
```

That is infrastructure, not data. Rerunning the same manifest with `-r2` names
put both on fresh VMs; this time they got past the bootstrap stage and kept
running. The lesson is worth keeping in the runbook: **check whether a failure
happened before or after the pipeline started**. `omx ws analysis logs` makes
that obvious.

The completed source job ran in 19m 23s and cost 3,184 VND. The platform's
pre-launch estimate for a 1-hour job with the same shape was 9,284 VND, so the
estimate is a ceiling, not a bill.

---

## Cost and sizing notes

The source job used:

```text
compute:  cloud / GreenNode-HCM
flavor:   code-a
region:   HCM03-1A
cpu:      16
memory:   32 GB
disk:     100 GB
time:     1 hour
```

Five concurrent jobs means five VMs. If the budget is tight, submit two or
three at a time instead of all five; the per-sample manifest does not change.
If one sample is much larger, override only that job:

```bash
omx ws analysis rerun "$SOURCE_JOB" -w "$WORKSPACE" \
    -n bacass-ERR14693661 \
    --cpu 32 --memory 64 --disk 200 --time 2h \
    -p input=s3://vieomics-prod/data/bacass/samplesheets/ERR14693661.tsv
```

---

## Gotchas

- **One row per job.** Do not point five jobs at the same five-row sheet unless
  you want each job to assemble all five samples.
- **Output prefix must be per-job.** `.../bacass/$job_id` is safe. A fixed
  `.../bacass` means the last job wins.
- **Quote the `-p` value.** S3 URLs contain `:` and sometimes `?`; quote them.
- **`--search` matches job name and tool**, not params. Use `--status` for
  exact state filters.
- **Job names are labels, not keys.** Two jobs can share a name; the job ID is
  the identity. Keep the sample accession in the name anyway.
- **A failed pre-pipeline bootstrap is retryable.** A failed pipeline task may
  need `-resume` semantics or a parameter fix, not just a blind rerun.
- **Do not put secrets in job names or samplesheet paths.** They end up in
  logs, manifests and audit records.

---

## Appendix: the same thing in Python

The `omx` CLI is convenient, but the client is a normal Python SDK. This is the
whole submission loop:

```python
from omicslab import Client

client = Client()
workspace = "<workspace-id>"
source_job = "<source-job-id>"
samples = [
    "ERR14693661",
    "ERR14693662",
    "ERR14693663",
    "ERR14693664",
    "ERR14693665",
]

for sample in samples:
    job = client.jobs.rerun_analysis(
        workspace,
        source_job,
        name=f"bacass-{sample}",
        params={
            "input": (
                "s3://vieomics-prod/data/bacass/samplesheets/"
                f"{sample}.tsv"
            )
        },
    )
    print(job["id"], job["name"], job["status"])
```

The Python call takes the same overrides as the CLI: `name`, `params`, `cpu`,
`memory`, `disk`, `time`, `compute_id`, `compute_type`, `flavor_type` and
`region`.

---

## Appendix: when there is no source job

If you do not have a completed job to copy, use a launch manifest instead.
Generate or edit an `*.omxa.json` file, change `params.input` and `name`, upload
it to the workspace, and launch it:

```bash
omx ls nf-core/bacass/2.6.1
omx ws analysis config launch \
    nf-core/bacass/2.6.1/test_full_from_scratch.omxa.json \
    -w "$WORKSPACE" -n bacass-ERR14693661
```

The manifest path is relative to the workspace `data/` prefix. For five
samples, create five manifests, each with a different `params.input` and
`name`. `rerun` is less error-prone once a known-good job exists, which is why
the main workflow above starts there.
