---
name: OmicsLab job launch
description: Launch and monitor OmicsLab analysis jobs from stored .omxa.json manifests, including token config, broker bypass, S3 input troubleshooting, and job status checks.
---

# OmicsLab job launch

Use this when launching an nf-core pipeline or other analysis on OmicsLab from
an `.omxa.json` manifest.

## 1. Authentication

The Studio normally routes `omx` through a credential broker. The broker allows
storage operations but blocks launch/create/rerun with:

```text
ForbiddenError: request not allowed by credential broker
```

When the user provides a real platform token, run with the broker disabled:

```bash
export OMICSLAB_TOKEN='<token>'
export OMICSLAB_CONFIG_DIR=/tmp/opencode/omicslab-token
mkdir -p "$OMICSLAB_CONFIG_DIR"
chmod 700 "$OMICSLAB_CONFIG_DIR"
```

Write a temporary config with the platform base URL and workspace:

```json
{
  "profiles": {
    "default": {
      "base_url": "https://platform.omicslab.io/api/v1",
      "workspace_id": "<workspace-id>",
      "endpoint_url": "https://s3-hcm-r2.s3cloud.vn"
    }
  }
}
```

```bash
chmod 600 "$OMICSLAB_CONFIG_DIR/config.json"
env -u OMICSLAB_BROKER_SOCKET \
  OMICSLAB_CONFIG_DIR="$OMICSLAB_CONFIG_DIR" \
  OMICSLAB_TOKEN="$OMICSLAB_TOKEN" \
  omx whoami
```

Never commit the token or the temporary config. Prefer the token environment
variable over writing the token into the config file.

## 2. Find the versioning credential

The manifest needs a `versioning_id` (the GitHub credential used to clone the
pipeline). Recover it from a known-good manifest in the workspace:

```bash
omx download analysis/bacass/ERR14693661.omxa.json /tmp/bacass.omxa.json \
  -w "$WORKSPACE" -y
```

Use its `versioning_id` for a new manifest. Do not commit the value; keep a
`__VERSIONING_ID__` placeholder in checked-in templates.

## 3. Create the manifest

Required top-level fields:

```json
{
  "job_type": "analysis",
  "name": "<job-name>",
  "git": "https://github.com/nf-core/fetchngs.git",
  "tag": "1.13.0",
  "commit_hash": "<full-commit>",
  "versioning_id": "<credential-id>",
  "profile": "test_full",
  "compute_type": "cloud",
  "flavor_type": "code-a",
  "region": "HCM03-1A",
  "cpu": 4,
  "memory": 8,
  "disk": 100,
  "time": 3600,
  "params": {
    "input": "s3://<bucket>/data/datasets/<project>/ids/SRR31184429.csv",
    "outdir": "s3://<bucket>/data/datasets/<project>/fetchngs-test/$job_id",
    "download_method": "sratools"
  }
}
```

Rules:

- `params.input` and `params.outdir` use the **full S3 URI** with `/data/`.
- Upload the input file under the **key without** `data/`.
- `$job_id` and `${job_id}` are expanded by the platform.
- Pin `tag` and `commit_hash`; do not use a moving branch.
- Use `profile: test_full` when reusing the established OmicsLab baseline, but
  override the pipeline params explicitly.

## 4. Upload and launch

```bash
omx ws analysis config upload /tmp/fetchngs.omxa.json \
  --key analysis/fetchngs/SRR31184429.omxa.json \
  -w "$WORKSPACE"

env -u OMICSLAB_BROKER_SOCKET \
  OMICSLAB_CONFIG_DIR="$OMICSLAB_CONFIG_DIR" \
  OMICSLAB_TOKEN="$OMICSLAB_TOKEN" \
  omx ws analysis config launch analysis/fetchngs/SRR31184429.omxa.json \
  -w "$WORKSPACE" \
  -n fetchngs-SRR31184429-test \
  --cpu 4 --memory 8 --disk 100 --time 1h \
  --compute "$COMPUTE_ID" \
  --compute-type cloud --flavor-type code-a
```

`config launch` reads the manifest from workspace storage, so the uploaded file
is the source of truth. Use `config upload` again after editing the manifest.

## 5. Monitor

```bash
env -u OMICSLAB_BROKER_SOCKET \
  OMICSLAB_CONFIG_DIR="$OMICSLAB_CONFIG_DIR" \
  OMICSLAB_TOKEN="$OMICSLAB_TOKEN" \
  omx ws analysis list -w "$WORKSPACE" \
  --search fetchngs-SRR31184429-test --json

env -u OMICSLAB_BROKER_SOCKET \
  OMICSLAB_CONFIG_DIR="$OMICSLAB_CONFIG_DIR" \
  OMICSLAB_TOKEN="$OMICSLAB_TOKEN" \
  omx ws analysis logs "$JOB_ID" -w "$WORKSPACE"
```

Terminal states: `completed`, `failed`, `cancelled`. The list payload includes
`running_time` (seconds), `running_cost`, `compute_cost`, and `platform_fee`.

## 6. Troubleshooting

### `the file or directory 's3://...' does not exist`

This is usually the upload-key/URI mismatch, not a missing file.

1. Check the key:
   `omx ls datasets/<project>/ids/ -w "$WORKSPACE" --json`
2. Download the exact manifest URI:
   `omx download s3://<bucket>/data/datasets/<project>/ids/<file> /tmp/x -w "$WORKSPACE"`
3. If the key works but the job still sees the raw `s3://` path, the platform
   did not localize the input before nf-schema validation. Use a known-working
   HTTPS input for that test, or fix the platform data preparation path.

### Broker errors

- `ForbiddenError: request not allowed by credential broker` means the command
  needs a real token or must be run from the platform UI.
- `config upload` may work while `config launch` is blocked; they are separate
  permissions.

### Job stays `running` with 0s

Check `omx ws analysis logs`; the platform may still be provisioning the VM.
Log lines start with `[STEP n/7]`. A failure during step 6 is a pipeline
failure, not infrastructure.

## Verified example

`fetchngs` 1.13.0, commit `955c892d80927cee633765e6e390f9cc6b7235c9`:

- Manifest: `analysis/fetchngs/SRR31184429.omxa.json`
- Input: `s3://vieomics-prod/data/datasets/gianglabs/47-samples/ids/SRR31184429.csv`
- Storage key: `datasets/gianglabs/47-samples/ids/SRR31184429.csv`
- Job: `fetchngs-SRR31184429-test-r3`
- Resource shape: 4 CPU / 8 GB / 100 GB / 1 h
- Download method: `sratools`

The job passed parameter validation and reached the SRA prefetch step with this
layout.
