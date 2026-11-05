# Five samples, five jobs: portable `nf-core/bacass` launches on OmicsLab

*How to run one analysis job per sample with a checked-in launch manifest and a
plain bash script.*

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
with `nf-core/bacass` 2.6.1. It assumes no previous job in your workspace: the
job definition lives in a small, portable `*.omxa.json` manifest that is
checked into this repository.

---

## What you need

- the `omx` CLI / SDK (this walkthrough uses `omicslab v2.6.0`);
- an OmicsLab account with access to the target workspace;
- a GitHub **versioning credential** in that account;
- `bash`, `sed` and `awk` — no Python required.

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

This repository already keeps one sheet per run under
`samplesheets/omicslab/`, each containing a single row:

```text
samplesheets/omicslab/ERR14693661.tsv
samplesheets/omicslab/ERR14693662.tsv
samplesheets/omicslab/ERR14693663.tsv
samplesheets/omicslab/ERR14693664.tsv
samplesheets/omicslab/ERR14693665.tsv
```

If you start from a combined sheet, split it with the bash helper:

```bash
bin/split_bacass_samplesheet.sh \
    --input bacass_samplesheet.tsv \
    --outdir samplesheets/local \
    --sample-regex 'ERR[0-9]+'
```

The `--sample-regex` is optional. By default the script names each output file
from the `ID` column. The regex is useful when `ID` is an ENA experiment
accession (`ERX...`) but you want the run accession (`ERR...`) in filenames and
job names.

---

## Step 2: understand the manifest

The job definition is
[`manifests/bacass.omxa.json`](../manifests/bacass.omxa.json). It is a normal
OmicsLab launch config with four placeholders:

| Placeholder | Filled with |
|---|---|
| `__SAMPLE__` | run accession, e.g. `ERR14693661` |
| `__BUCKET__` | the workspace storage bucket |
| `__VERSIONING_ID__` | your GitHub versioning credential ID |
| `__REGION__` | GreenNode zone, e.g. `HCM03-1A` |

The important fields are top-level, not buried in params:

```json
{
  "job_type": "analysis",
  "name": "bacass-__SAMPLE__",
  "git": "https://github.com/nf-core/bacass.git",
  "tag": "2.6.1",
  "commit_hash": "5ed7c2dd9a05d2434d8ba39ace1116368a4ba570",
  "versioning_id": "__VERSIONING_ID__",
  "profile": "test_full",
  "cpu": 16,
  "memory": 32,
  "disk": 100,
  "time": 3600,
  "params": {
    "input": "s3://__BUCKET__/data/bacass/samplesheets/__SAMPLE__.tsv",
    "outdir": "s3://__BUCKET__/data/bacass/$job_id"
  }
}
```

Two details matter:

- **`profile` is top-level**, not `params.profile`.
- **`params.outdir` contains `$job_id`**, so every job publishes into its own
  prefix. A fixed output prefix would let the last job win.

The manifest is deliberately self-contained: it does not reference an existing
job in anyone's workspace. Any user with their own workspace and their own
GitHub credential can launch it.

---

## Step 3: find your versioning credential

The backend needs a GitHub credential to clone the pipeline, and the credential
belongs to **you**, not to the repository. Find its ID in the platform UI:

1. open **Settings → Credentials → GitHub**;
2. create or reuse a GitHub credential with access to `nf-core/bacass`;
3. copy its **credential ID** (a UUID).

Store it once for your current `omx` profile:

```bash
omx use --versioning <credential-id>
omx use show          # confirms the stored versioning value
```

Or pass it explicitly for a single run:

```bash
export VERSIONING_ID=<credential-id>
```

The submission script checks `VERSIONING_ID` first, then the value stored by
`omx use --versioning`, and stops with a clear message if neither is set.

---

## Step 4: dry run first

The helper does two things:

1. it launches the **first** sample from the checked-in manifest, creating a
   real job in *your* workspace;
2. it reuses that new job with `omx ws analysis rerun` for the remaining
   samples, changing only the name and `params.input`.

```bash
cd ndm-truncation-reanalysis

export WORKSPACE=<workspace-id>
export VERSIONING_ID=<credential-id>

DRY_RUN=1 bin/submit_bacass_jobs.sh \
    ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665
```

`DRY_RUN=1` prints every command without touching the platform. The first
sample is the bootstrap:

```text
omx upload samplesheets/omicslab/ERR14693661.tsv \
    s3://<bucket>/data/bacass/samplesheets/ERR14693661.tsv -y
sed -e s|__SAMPLE__|ERR14693661|g ... manifests/bacass.omxa.json \
    > manifests/generated/ERR14693661.omxa.json
omx ws analysis config upload manifests/generated/ERR14693661.omxa.json \
    --key analysis/bacass/ERR14693661.omxa.json -w <workspace-id>
omx ws analysis config launch analysis/bacass/ERR14693661.omxa.json \
    -w <workspace-id> -n bacass-ERR14693661 --compute <compute-id> \
    --compute-type cloud --cpu 16 --memory 32 --disk 100 --time 3600 \
    --flavor-type code-a
```

Every later sample is a rerun of that new job:

```text
omx upload samplesheets/omicslab/ERR14693662.tsv \
    s3://<bucket>/data/bacass/samplesheets/ERR14693662.tsv -y
omx ws analysis rerun <new-job-id> -w <workspace-id> \
    -n bacass-ERR14693662 \
    -p input=s3://<bucket>/data/bacass/samplesheets/ERR14693662.tsv --json
```

---

## Step 5: launch

Drop `DRY_RUN=1`:

```bash
bin/submit_bacass_jobs.sh \
    ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665
```

With no sample arguments, the script submits every `*.tsv` in
`samplesheets/omicslab/`:

```bash
bin/submit_bacass_jobs.sh
```

The script prints the new job ID after the manifest launch, then reruns it for
the other four samples. Each job is named `bacass-<sample>` and writes to its
own `s3://<bucket>/data/bacass/<job-id>` prefix.

If you already have a good bacass job in your workspace, skip the manifest
launch and rerun that job for every sample:

```bash
SOURCE_JOB=<job-id> bin/submit_bacass_jobs.sh \
    ERR14693661 ERR14693662 ERR14693663 ERR14693664 ERR14693665
```

That mode needs no `VERSIONING_ID`: rerun copies the tool, tag, pinned commit,
versioning credential and resource shape from the source job.

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

If one job fails, rerun the source job with a new name:

```bash
omx ws analysis rerun <source-job-id> \
    -w "$WORKSPACE" \
    -n bacass-ERR14693661-r2 \
    -p input=s3://<bucket>/data/bacass/samplesheets/ERR14693661.tsv \
    --json
```

Rerun copies the resolved manifest, so a retry cannot drift to a different tag,
commit or parameter set. The source job is one you created, not a job that
happens to exist in someone else's workspace.

---

## What this looked like on the five isolates

| Run | Isolate | Species | Job name |
|---|---|---|---|
| ERR14693661 | 03-A-063 | *K. pneumoniae* | `bacass-ERR14693661` |
| ERR14693662 | 03-A-038 | *K. pneumoniae* | `bacass-ERR14693662` |
| ERR14693663 | 24-A-028 | *K. pneumoniae* | `bacass-ERR14693663` |
| ERR14693664 | 11-A-427 | *K. pneumoniae* | `bacass-ERR14693664` |
| ERR14693665 | 021-A-244 | *P. aeruginosa* | `bacass-ERR14693665` |

The manifest pins `nf-core/bacass` 2.6.1 at commit `5ed7c2dd…`, the same
pipeline version as the original investigation.

Two earlier attempts failed before Nextflow started:

```text
Cloud VM setup timed out: SSH command exceeded 289.851s
Cloud VM setup timed out: bootstrap exceeded the 300s total deadline
```

That is infrastructure, not data. Relaunching the same job with an `-r2`
name put both on fresh VMs; this time they got past the bootstrap stage and kept
running. The lesson is worth keeping in the runbook: **check whether a failure
happened before or after the pipeline started**. `omx ws analysis logs` makes
that obvious.

On this run, the first manifest launch created `bacass-ERR14693661` (job
`b9785600-…`). Rerunning that job for `ERR14693665` created `becd18ee-…`, and
the API reported exactly one change:

```json
"changed_parameters": [
  {
    "field": "params.input",
    "old": "s3://vieomics-prod/data/bacass/samplesheets/ERR14693661.tsv",
    "new": "s3://vieomics-prod/data/bacass/samplesheets/ERR14693665.tsv"
  }
]
```

That is the whole audit trail: same pipeline, same commit, same resource shape,
one input swapped.

The completed source job ran in 19m 23s and cost 3,184 VND. The platform's
pre-launch estimate for a 1-hour job with the same shape was 9,284 VND, so the
estimate is a ceiling, not a bill.

---

## Cost and sizing notes

The manifest uses:

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
three at a time instead of all five; the manifest does not change.
The script also accepts overrides, so you can shrink a pilot run or enlarge one
difficult sample without editing the template:

```bash
CPU=4 MEMORY=8 DISK=50 TIME=2h \
    bin/submit_bacass_jobs.sh ERR14693661
```

The launch flags override the resource values in the manifest for that run
only. The checked-in manifest stays the default.

---

## Gotchas

- **One row per job.** Do not point five jobs at the same five-row sheet unless
  you want each job to assemble all five samples.
- **Output prefix must be per-job.** `.../bacass/$job_id` is safe. A fixed
  `.../bacass` means the last job wins.
- **`profile` is top-level.** Putting it under `params` is silently ignored.
- **The versioning credential is personal.** Do not commit a rendered manifest
  that contains your credential ID. `manifests/generated/` is git-ignored.
- **`--search` matches job name and tool**, not params. Use `--status` for
  exact state filters.
- **Job names are labels, not keys.** Two jobs can share a name; the job ID is
  the identity. Keep the sample accession in the name anyway.
- **A failed pre-pipeline bootstrap is retryable.** A failed pipeline task may
  need a parameter fix or more resources, not just a blind relaunch.
- **Do not put secrets in job names or samplesheet paths.** They end up in
  logs, manifests and audit records.

---

## Appendix: launch one sample by hand

Everything the script does can be done by hand. The first sample is the
manifest launch; the rest are reruns of it:

```bash
cd ndm-truncation-reanalysis
SAMPLE=ERR14693661
BUCKET=$(omx ws get "$WORKSPACE" | awk -F': ' '/^bucket_name:/ {print $2}')
COMPUTE=$(omx ws get "$WORKSPACE" \
    | awk -F': ' '/^default_analysis_compute_id:/ {print $2}')

mkdir -p manifests/generated
sed -e "s|__SAMPLE__|$SAMPLE|g" \
    -e "s|__BUCKET__|$BUCKET|g" \
    -e "s|__VERSIONING_ID__|$VERSIONING_ID|g" \
    -e "s|__REGION__|HCM03-1A|g" \
    manifests/bacass.omxa.json > "manifests/generated/$SAMPLE.omxa.json"

omx upload "samplesheets/omicslab/$SAMPLE.tsv" \
    "s3://$BUCKET/data/bacass/samplesheets/$SAMPLE.tsv" -y

omx ws analysis config upload "manifests/generated/$SAMPLE.omxa.json" \
    --key "analysis/bacass/$SAMPLE.omxa.json" -w "$WORKSPACE"

omx ws analysis config launch "analysis/bacass/$SAMPLE.omxa.json" \
    -w "$WORKSPACE" -n "bacass-$SAMPLE" --compute "$COMPUTE" \
    --compute-type cloud --cpu 16 --memory 32 --disk 100 --time 3600 \
    --flavor-type code-a

JOB=<new-job-id>   # printed by the launch command above
```

Then rerun the new job for each remaining sample:

```bash
for SAMPLE in ERR14693662 ERR14693663 ERR14693664 ERR14693665; do
    omx upload "samplesheets/omicslab/$SAMPLE.tsv" \
        "s3://$BUCKET/data/bacass/samplesheets/$SAMPLE.tsv" -y
    omx ws analysis rerun "$JOB" -w "$WORKSPACE" -n "bacass-$SAMPLE" \
        -p "input=s3://$BUCKET/data/bacass/samplesheets/$SAMPLE.tsv" --json
done
```

No external source job, no Python, no hidden state: the first job comes from a
checked-in manifest, and every later sample is an exact copy with one input
swapped.
