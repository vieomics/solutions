---
name: OmicsLab data staging
description: Upload, list, download, and verify files in OmicsLab workspace storage with the correct key and S3 URI conventions.
---

# OmicsLab data staging

Use this when moving inputs, samplesheets, manifests, or results into or out of
an OmicsLab workspace.

## Key rule: the `data/` prefix is virtual

Workspace storage keys are relative to the platform's virtual `data/` prefix.

| Purpose | Form |
|---|---|
| Upload key | `datasets/<project>/...` |
| List key | `datasets/<project>/...` |
| Full S3 URI | `s3://<bucket>/data/datasets/<project>/...` |

Do **not** add `data/` to an upload key. Do **not** omit `/data` from a full
S3 URI used in a manifest.

Example, for workspace `vieomics-prod`:

```bash
# Upload
omx upload ids.single.csv datasets/gianglabs/47-samples/ids/SRR31184429.csv \
  -w "$WORKSPACE" -y

# Verify by key
omx ls datasets/gianglabs/47-samples/ids/ -w "$WORKSPACE" --json

# Verify by the exact S3 URI that goes into the manifest
omx download \
  s3://vieomics-prod/data/datasets/gianglabs/47-samples/ids/SRR31184429.csv \
  /tmp/verify.csv -w "$WORKSPACE" -y
```

If the key has `data/...`, the full URI needs `data/data/...` and the manifest
will usually fail. Keep upload keys and manifest URIs in the two forms above.

## Workspace discovery

```bash
omx ws list
omx ws get "$WORKSPACE"
```

`omx ws get` returns `bucket_name`, `endpoint_url`, and the default compute ID.

## Public vs private workspaces

- Private workspaces are the safe place for job inputs created during a run.
- The public `Omicslab` workspace (`bucket_name: omicslab`) is used for shared
  references and datasets. Uploads there may return `Forbidden` even when the
  account is an admin. Do not assume write access.
- Existing public data uses `s3://omicslab/data/datasets/...` in manifests,
  while the corresponding storage key is `datasets/...`.

## Verification checklist

1. `omx ls <key>/ --json` shows the file and expected size.
2. `omx download s3://<bucket>/data/<key>` succeeds.
3. The downloaded bytes match the local file.
4. The manifest contains the full S3 URI, not the upload key.
5. No secrets or tokens are written into paths, filenames, or manifests.

## Related skill

See `omicslab-job-launch` for turning staged inputs into analysis jobs.
