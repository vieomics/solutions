#!/usr/bin/env bash
# Download FASTQ files with the NCBI SRA Toolkit.
#
# Default project: PRJNA1180080 (Norris et al. 2026, 47 B. pseudomallei runs)
#
# Usage:
#   bash download_sra_fastq.sh                    # all runs in ids.csv
#   bash download_sra_fastq.sh SRR31184429        # one run only
#
# Environment:
#   OUTDIR          default: /content/data/PRJNA1180080
#   IDS_FILE        default: ../ids.csv (relative to this script)
#   PREFETCH_JOBS   parallel prefetch downloads, default: 4
#   CONVERT_JOBS    parallel fasterq-dump jobs, default: 2
#   THREADS         threads per fasterq-dump, default: 4
#   KEEP_SRA        set to 1 to keep .sra files, default: 0
#   MAPPING_TSV     optional: run_accession <TAB> isolate_name
#
# Requirements:
#   prefetch, fasterq-dump, vdb-validate on PATH (NCBI SRA Toolkit).
#
# Outputs:
#   $OUTDIR/fastq/*.fastq.gz
#   $OUTDIR/$PROJECT.bacass.tsv
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT="${PROJECT:-PRJNA1180080}"
OUTDIR="${OUTDIR:-/content/data/${PROJECT}}"
SRA_DIR="${SRA_DIR:-${OUTDIR}/sra}"
FASTQ_DIR="${FASTQ_DIR:-${OUTDIR}/fastq}"
TMP_DIR="${TMP_DIR:-${OUTDIR}/tmp}"
IDS_FILE="${IDS_FILE:-${SCRIPT_DIR}/../ids.csv}"
PREFETCH_JOBS="${PREFETCH_JOBS:-4}"
CONVERT_JOBS="${CONVERT_JOBS:-2}"
THREADS="${THREADS:-4}"
KEEP_SRA="${KEEP_SRA:-0}"
SAMPLESHEET="${SAMPLESHEET:-${OUTDIR}/${PROJECT}.bacass.tsv}"

for cmd in prefetch fasterq-dump; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "Missing ${cmd}. Install the NCBI SRA Toolkit first." >&2
    exit 1
  fi
done

mkdir -p "$SRA_DIR" "$FASTQ_DIR" "$TMP_DIR"

if [ "$#" -gt 0 ]; then
  runs=("$@")
else
  mapfile -t runs < <(grep -v '^[[:space:]]*$' "$IDS_FILE")
fi

if [ "${#runs[@]}" -eq 0 ]; then
  echo "No run accessions selected." >&2
  exit 1
fi

echo "Prefetching ${#runs[@]} runs with ${PREFETCH_JOBS} workers ..."
printf '%s\n' "${runs[@]}" | xargs -r -P "$PREFETCH_JOBS" -I{} \
  prefetch "{}" --output-directory "$SRA_DIR"

if command -v vdb-validate >/dev/null 2>&1; then
  echo "Validating SRA files ..."
  for run in "${runs[@]}"; do
    vdb-validate "$SRA_DIR/$run/$run.sra"
  done
fi

convert_one() {
  local run="$1"
  local sra="$SRA_DIR/$run/$run.sra"

  if [ ! -f "$sra" ]; then
    echo "Missing ${sra}" >&2
    return 1
  fi

  fasterq-dump "$sra" \
    --outdir "$FASTQ_DIR" \
    --temp "$TMP_DIR" \
    --split-files \
    --skip-technical \
    --threads "$THREADS"

  for f in "$FASTQ_DIR/${run}_1.fastq" "$FASTQ_DIR/${run}_2.fastq"; do
    [ -f "$f" ] && gzip -f "$f"
  done

  if [ "$KEEP_SRA" != "1" ]; then
    rm -rf "$SRA_DIR/$run"
  fi
}
export -f convert_one
export SRA_DIR FASTQ_DIR TMP_DIR THREADS KEEP_SRA

echo "Converting to FASTQ with ${CONVERT_JOBS} workers ..."
printf '%s\n' "${runs[@]}" | xargs -r -P "$CONVERT_JOBS" -I{} \
  bash -c 'convert_one "$@"' _ {}

printf 'ID\tR1\tR2\tLongFastQ\tFast5\tGenomeSize\n' > "$SAMPLESHEET"

for run in "${runs[@]}"; do
  r1="${FASTQ_DIR}/${run}_1.fastq.gz"
  r2="${FASTQ_DIR}/${run}_2.fastq.gz"

  if [ ! -f "$r1" ]; then
    echo "Missing ${r1}" >&2
    exit 1
  fi
  [ -f "$r2" ] || r2="NA"

  id="$run"
  if [ -n "${MAPPING_TSV:-}" ] && [ -f "$MAPPING_TSV" ]; then
    mapped="$(awk -F'\t' -v r="$run" '$1 == r {print $2; exit}' "$MAPPING_TSV")"
    [ -n "$mapped" ] && id="$mapped"
  fi

  printf '%s\t%s\t%s\tNA\tNA\tNA\n' "$id" "$r1" "$r2" >> "$SAMPLESHEET"
done

echo
echo "Samplesheet: ${SAMPLESHEET}"
echo "Rows:        $(( $(wc -l < "$SAMPLESHEET") - 1 ))"
