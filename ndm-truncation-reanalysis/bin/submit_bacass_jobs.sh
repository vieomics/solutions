#!/usr/bin/env bash
# Run one nf-core/bacass analysis job per sample on OmicsLab.
#
# The first sample is launched from the portable manifest
# manifests/bacass.omxa.json. That creates a real job in *your* workspace, so
# the remaining samples can reuse it with `omx ws analysis rerun`:
#
#   sample 1 -> new job from manifest
#   sample 2 -> rerun sample 1 with a different input sheet
#   sample 3 -> rerun sample 1 with a different input sheet
#   ...
#
# No source job from another workspace is required.
#
# Usage:
#   WORKSPACE=<workspace-id> VERSIONING_ID=<github-credential-id> \
#     bin/submit_bacass_jobs.sh ERR14693661 ERR14693662 ERR14693663
#
#   # Reuse an existing job instead of launching the first sample again:
#   WORKSPACE=<workspace-id> SOURCE_JOB=<job-id> \
#     bin/submit_bacass_jobs.sh ERR14693662 ERR14693663
#
# With no sample arguments, every *.tsv in SAMPLESHEET_DIR is submitted.
#
# Environment:
#   WORKSPACE        OmicsLab workspace ID (required)
#   VERSIONING_ID    GitHub versioning credential ID (required only when the
#                    first sample is launched from the manifest; ignored with
#                    SOURCE_JOB)
#   SOURCE_JOB       existing job to rerun for every sample (skips the manifest)
#   BUCKET           workspace storage bucket (default: from `omx ws get`)
#   COMPUTE_ID       compute credential ID (default: workspace default)
#   COMPUTE_TYPE     cloud or runner (default: cloud)
#   FLAVOR_TYPE      cloud VM flavor (default: code-a)
#   REGION           GreenNode zone baked into the manifest (default: HCM03-1A)
#   CPU / MEMORY     job resources (default: 16 / 32)
#   DISK / TIME      disk GB and time limit (default: 100 / 3600)
#   SAMPLESHEET_DIR  local dir with <sample>.tsv (default: samplesheets/omicslab)
#   TEMPLATE         manifest template (default: manifests/bacass.omxa.json)
#   MANIFEST_DIR     rendered manifest (default: manifests/generated)
#   MANIFEST_PREFIX  workspace key prefix (default: analysis/bacass)
#   DRY_RUN=1        print the commands without uploading or submitting
set -euo pipefail

WORKSPACE="${WORKSPACE:?set WORKSPACE to the OmicsLab workspace ID}"
SOURCE_JOB="${SOURCE_JOB:-}"
COMPUTE_TYPE="${COMPUTE_TYPE:-cloud}"
FLAVOR_TYPE="${FLAVOR_TYPE:-code-a}"
REGION="${REGION:-HCM03-1A}"
CPU="${CPU:-16}"
MEMORY="${MEMORY:-32}"
DISK="${DISK:-100}"
TIME="${TIME:-3600}"
SAMPLESHEET_DIR="${SAMPLESHEET_DIR:-samplesheets/omicslab}"
TEMPLATE="${TEMPLATE:-manifests/bacass.omxa.json}"
MANIFEST_DIR="${MANIFEST_DIR:-manifests/generated}"
MANIFEST_PREFIX="${MANIFEST_PREFIX:-analysis/bacass}"

cd "$(dirname "$0")/.."

# Resolve values that are specific to the caller's workspace.
ws_info="$(omx ws get "$WORKSPACE")"
if [ -z "${BUCKET:-}" ]; then
    BUCKET="$(printf '%s\n' "$ws_info" | awk -F': ' '/^bucket_name:/ {print $2; exit}')"
fi
if [ -z "${BUCKET:-}" ] || [ "$BUCKET" = "—" ]; then
    echo "Could not resolve a bucket for workspace $WORKSPACE" >&2
    exit 1
fi

# The manifest launch needs a compute and a GitHub credential. A rerun copies
# both from the source job, so it needs neither.
if [ -z "$SOURCE_JOB" ]; then
    if [ -z "${COMPUTE_ID:-}" ]; then
        COMPUTE_ID="$(printf '%s\n' "$ws_info" \
            | awk -F': ' '/^default_analysis_compute_id:/ {print $2; exit}')"
    fi
    if [ -z "${COMPUTE_ID:-}" ] || [ "$COMPUTE_ID" = "—" ]; then
        echo "Could not resolve a default compute for workspace $WORKSPACE" >&2
        exit 1
    fi

    if [ -z "${VERSIONING_ID:-}" ]; then
        config_file="${CONFIG_FILE:-${OMICSLAB_CONFIG_DIR:-$HOME/.omicslab}/config.json}"
        if [ -f "$config_file" ]; then
            VERSIONING_ID="$(grep -o '"versioning_id"[[:space:]]*:[[:space:]]*"[^"]*"' "$config_file" \
                | head -1 | sed -E 's/.*"([^"]*)"$/\1/')"
        fi
    fi
    case "${VERSIONING_ID:-}" in
        "" | "not set" | "notset")
            cat >&2 <<'EOF'
No GitHub versioning credential set.

The OmicsLab backend needs a GitHub credential to clone nf-core/bacass.
Find your credential ID in the platform UI (Settings -> Credentials -> GitHub),
then either:

  export VERSIONING_ID=<credential-id>
  # or store it once for this profile:
  omx use --versioning <credential-id>

Then run this script again. If you already have a job in this workspace, you
can skip the manifest launch entirely with SOURCE_JOB=<job-id>.
EOF
            exit 1
            ;;
    esac
fi

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

samples=("$@")
for sample in "${samples[@]}"; do
    if [ ! -f "$SAMPLESHEET_DIR/$sample.tsv" ]; then
        echo "Missing samplesheet: $SAMPLESHEET_DIR/$sample.tsv" >&2
        exit 1
    fi
done

s3_sheet_for() {
    printf 's3://%s/data/bacass/samplesheets/%s.tsv\n' "$BUCKET" "$1"
}

upload_sheet() {
    omx upload "$SAMPLESHEET_DIR/$1.tsv" "$(s3_sheet_for "$1")" -y
}

rerun_for() {
    local source_job="$1" sample="$2"
    omx ws analysis rerun "$source_job" \
        -w "$WORKSPACE" \
        -n "bacass-$sample" \
        -p "input=$(s3_sheet_for "$sample")" \
        --cpu "$CPU" --memory "$MEMORY" --disk "$DISK" --time "$TIME" \
        --compute-type "$COMPUTE_TYPE" --flavor-type "$FLAVOR_TYPE" \
        --json
}

mkdir -p "$MANIFEST_DIR"

# Mode 1: reuse an existing job for every sample.
if [ -n "$SOURCE_JOB" ]; then
    for sample in "${samples[@]}"; do
        if [ "${DRY_RUN:-0}" = "1" ]; then
            printf 'omx upload %q %q -y\n' \
                "$SAMPLESHEET_DIR/$sample.tsv" "$(s3_sheet_for "$sample")"
            printf 'omx ws analysis rerun %q -w %q -n %q -p %q --cpu %q --memory %q --disk %q --time %q --compute-type %q --flavor-type %q --json\n' \
                "$SOURCE_JOB" "$WORKSPACE" "bacass-$sample" \
                "input=$(s3_sheet_for "$sample")" \
                "$CPU" "$MEMORY" "$DISK" "$TIME" "$COMPUTE_TYPE" "$FLAVOR_TYPE"
            continue
        fi
        upload_sheet "$sample"
        rerun_for "$SOURCE_JOB" "$sample"
    done
    exit 0
fi

# Mode 2: launch the first sample from the manifest, then rerun that new job.
first="${samples[0]}"
first_s3_sheet="$(s3_sheet_for "$first")"
first_manifest="$MANIFEST_DIR/$first.omxa.json"
first_key="$MANIFEST_PREFIX/$first.omxa.json"

render=(sed
    -e "s|__SAMPLE__|$first|g"
    -e "s|__BUCKET__|$BUCKET|g"
    -e "s|__VERSIONING_ID__|${VERSIONING_ID:-}|g"
    -e "s|__REGION__|$REGION|g"
    "$TEMPLATE")

launch=(omx ws analysis config launch "$first_key" -w "$WORKSPACE" \
    -n "bacass-$first" --compute "$COMPUTE_ID" \
    --compute-type "$COMPUTE_TYPE" \
    --cpu "$CPU" --memory "$MEMORY" --disk "$DISK" --time "$TIME")
if [ -n "$FLAVOR_TYPE" ]; then
    launch+=(--flavor-type "$FLAVOR_TYPE")
fi

if [ "${DRY_RUN:-0}" = "1" ]; then
    printf 'omx upload %q %q -y\n' \
        "$SAMPLESHEET_DIR/$first.tsv" "$first_s3_sheet"
    printf '%q ' "${render[@]}"; printf '> %q\n' "$first_manifest"
    printf 'omx ws analysis config upload %q --key %q -w %q\n' \
        "$first_manifest" "$first_key" "$WORKSPACE"
    printf '%q ' "${launch[@]}"; echo
    for sample in "${samples[@]:1}"; do
        printf 'omx upload %q %q -y\n' \
            "$SAMPLESHEET_DIR/$sample.tsv" "$(s3_sheet_for "$sample")"
        printf 'omx ws analysis rerun <new-job-id> -w %q -n %q -p %q --cpu %q --memory %q --disk %q --time %q --compute-type %q --flavor-type %q --json\n' \
            "$WORKSPACE" "bacass-$sample" "input=$(s3_sheet_for "$sample")" \
            "$CPU" "$MEMORY" "$DISK" "$TIME" "$COMPUTE_TYPE" "$FLAVOR_TYPE"
    done
    exit 0
fi

upload_sheet "$first"
"${render[@]}" > "$first_manifest"
omx ws analysis config upload "$first_manifest" --key "$first_key" -w "$WORKSPACE"

launch_output="$("${launch[@]}" 2>&1)"
printf '%s\n' "$launch_output"
new_job_id="$(printf '%s\n' "$launch_output" | awk -F': ' '/^id:/ {print $2; exit}')"
if [ -z "$new_job_id" ]; then
    echo "Could not read the new job ID from the launch output." >&2
    exit 1
fi
echo "First job launched: $new_job_id"

for sample in "${samples[@]:1}"; do
    upload_sheet "$sample"
    rerun_for "$new_job_id" "$sample"
done
