#!/usr/bin/env bash
# Download FASTQ files for an ENA/SRA BioProject.
#
# Default project: PRJNA1180080 (Norris et al. 2026, 47 B. pseudomallei runs)
#
# Usage:
#   bash download_ena_fastq.sh                    # all runs in the project
#   bash download_ena_fastq.sh SRR31184429        # one run only
#   PROJECT=PRJNA1180080 OUTDIR=/content/data/PRJNA1180080 JOBS=6 \
#       bash download_ena_fastq.sh
#
# Optional:
#   MAPPING_TSV=/path/to/map.tsv   # columns: run_accession <TAB> isolate_name
#   SCHEME=ftp                     # fallback if https://ftp.sra.ebi.ac.uk fails
#
# Outputs:
#   $OUTDIR/fastq/*.fastq.gz
#   $OUTDIR/metadata/$PROJECT.ena.tsv
#   $OUTDIR/metadata/$PROJECT.fastq_urls.txt
#   $OUTDIR/metadata/$PROJECT.md5
#   $OUTDIR/$PROJECT.bacass.tsv
set -euo pipefail

PROJECT="${PROJECT:-PRJNA1180080}"
OUTDIR="${OUTDIR:-/content/data/${PROJECT}}"
FASTQ_DIR="${FASTQ_DIR:-${OUTDIR}/fastq}"
META_DIR="${META_DIR:-${OUTDIR}/metadata}"
JOBS="${JOBS:-6}"
SCHEME="${SCHEME:-https}"
ENA_API="${ENA_API:-https://www.ebi.ac.uk/ena/portal/api/filereport}"
FIELDS="run_accession,sample_accession,library_layout,fastq_ftp,fastq_md5,read_count,base_count"
REPORT="${META_DIR}/${PROJECT}.ena.tsv"
URLS="${META_DIR}/${PROJECT}.fastq_urls.txt"
MD5S="${META_DIR}/${PROJECT}.md5"
SAMPLESHEET="${OUTDIR}/${PROJECT}.bacass.tsv"
SELECTED="${META_DIR}/selected_runs.txt"

mkdir -p "$FASTQ_DIR" "$META_DIR"

echo "Fetching ENA metadata for ${PROJECT} ..."
curl -fsSL --retry 5 --retry-delay 5 \
  "${ENA_API}?accession=${PROJECT}&result=read_run&fields=${FIELDS}&format=tsv&limit=0" \
  -o "$REPORT"

if [ "$(wc -l < "$REPORT")" -le 1 ]; then
  echo "No runs found for ${PROJECT}" >&2
  exit 1
fi

if [ "$#" -gt 0 ]; then
  printf '%s\n' "$@" > "$SELECTED"
else
  tail -n +2 "$REPORT" | cut -f1 > "$SELECTED"
fi

: > "$URLS"
: > "$MD5S"

while IFS=$'\t' read -r run sample layout ftp md5 reads bases; do
  [ -n "${run:-}" ] || continue
  grep -qx "$run" "$SELECTED" || continue

  IFS=';' read -r -a urls <<< "$ftp"
  IFS=';' read -r -a sums <<< "$md5"

  for i in "${!urls[@]}"; do
    url="${urls[$i]}"
    [ -n "$url" ] || continue
    base="$(basename "$url")"
    printf '%s://%s\n' "$SCHEME" "$url" >> "$URLS"
    if [ -n "${sums[$i]:-}" ]; then
      printf '%s  %s\n' "${sums[$i]}" "$base" >> "$MD5S"
    fi
  done
done < <(tail -n +2 "$REPORT")

echo "Selected runs: $(wc -l < "$SELECTED")"
echo "FASTQ files:   $(wc -l < "$URLS")"
echo "Downloading to ${FASTQ_DIR} ..."

if command -v aria2c >/dev/null 2>&1; then
  aria2c -c -x 8 -s 8 -j "$JOBS" \
    -d "$FASTQ_DIR" -i "$URLS" \
    --auto-file-renaming=false --allow-overwrite=false
else
  echo "aria2c not found; falling back to wget (sequential)."
  while IFS= read -r url; do
    wget -c --tries=5 --timeout=60 -P "$FASTQ_DIR" "$url"
  done < "$URLS"
fi

if [ -s "$MD5S" ]; then
  echo "Verifying MD5 checksums ..."
  (cd "$FASTQ_DIR" && md5sum -c "$MD5S")
else
  echo "No MD5 values in ENA report; skipping verification."
fi

printf 'ID\tR1\tR2\tLongFastQ\tFast5\tGenomeSize\n' > "$SAMPLESHEET"

while IFS= read -r run; do
  [ -n "$run" ] || continue

  row="$(awk -F'\t' -v r="$run" 'NR > 1 && $1 == r {print; exit}' "$REPORT")"
  [ -n "$row" ] || continue

  ftp="$(printf '%s\n' "$row" | cut -f4)"
  IFS=';' read -r -a urls <<< "$ftp"

  r1=""
  r2="NA"
  [ "${#urls[@]}" -ge 1 ] && r1="${FASTQ_DIR}/$(basename "${urls[0]}")"
  [ "${#urls[@]}" -ge 2 ] && r2="${FASTQ_DIR}/$(basename "${urls[1]}")"

  id="$run"
  if [ -n "${MAPPING_TSV:-}" ] && [ -f "$MAPPING_TSV" ]; then
    mapped="$(awk -F'\t' -v r="$run" '$1 == r {print $2; exit}' "$MAPPING_TSV")"
    [ -n "$mapped" ] && id="$mapped"
  fi

  printf '%s\t%s\t%s\tNA\tNA\tNA\n' "$id" "$r1" "$r2" >> "$SAMPLESHEET"
done < "$SELECTED"

echo
echo "Samplesheet: ${SAMPLESHEET}"
echo "Rows:        $(( $(wc -l < "$SAMPLESHEET") - 1 ))"
