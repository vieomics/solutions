#!/usr/bin/env bash
# Submit one nf-core/bacass analysis job per sample on OmicsLab.
#
# Each run reuses a known-good source job (pipeline, tag, pinned commit,
# compute, resources and every param except `input`), uploads the one-row
# samplesheet to workspace storage, and overrides only the input path.
#
# Usage:
#   WORKSPACE=<workspace-id> SOURCE_JOB=<completed-bacass-job-id> \
#     bin/submit_bacass_jobs.sh ERR14693661 ERR14693662 ERR14693663
#
# With no sample arguments, every *.tsv in SAMPLESHEET_DIR is submitted.
#
# Environment:
#   WORKSPACE        OmicsLab workspace ID (required)
#   SOURCE_JOB       completed bacass job ID to copy (required)
#   SAMPLESHEET_DIR  local dir with <sample>.tsv (default: samplesheets/omicslab)
#   S3_PREFIX        workspace S3 prefix for the sheets
#                    (default: s3://vieomics-prod/data/bacass/samplesheets)
#   JOB_PREFIX       job name prefix (default: bacass)
#   DRY_RUN=1        print the commands without uploading or submitting
set -euo pipefail

WORKSPACE="${WORKSPACE:?set WORKSPACE to the OmicsLab workspace ID}"
SOURCE_JOB="${SOURCE_JOB:?set SOURCE_JOB to a completed bacass job ID}"
SAMPLESHEET_DIR="${SAMPLESHEET_DIR:-samplesheets/omicslab}"
S3_PREFIX="${S3_PREFIX:-s3://vieomics-prod/data/bacass/samplesheets}"
JOB_PREFIX="${JOB_PREFIX:-bacass}"

cd "$(dirname "$0")/.."

if [ "$#" -eq 0 ]; then
    shopt -s nullglob
    files=("$SAMPLESHEET_DIR"/*.tsv)
    if [ "${#files[@]}" -eq 0 ]; then
        echo "No samplesheets found in $SAMPLESHEET_DIR" >&2
        exit 1
    fi
    set -- "${files[@]##*/}"
    set -- "${@%.tsv}"
fi

for sample in "$@"; do
    sheet="$SAMPLESHEET_DIR/$sample.tsv"
    if [ ! -f "$sheet" ]; then
        echo "Missing samplesheet: $sheet" >&2
        exit 1
    fi

    s3_url="${S3_PREFIX%/}/$sample.tsv"
    name="$JOB_PREFIX-$sample"

    upload=(omx upload "$sheet" "$s3_url" -y)
    submit=(omx ws analysis rerun "$SOURCE_JOB" -w "$WORKSPACE" \
        -n "$name" -p "input=$s3_url" --json)

    if [ "${DRY_RUN:-0}" = "1" ]; then
        printf '%q ' "${upload[@]}"; echo
        printf '%q ' "${submit[@]}"; echo
        continue
    fi

    "${upload[@]}"
    "${submit[@]}"
done
