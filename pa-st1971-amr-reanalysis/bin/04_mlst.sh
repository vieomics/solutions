#!/usr/bin/env bash
# Step 4 - confirm the sequence type with the PubMLST Pseudomonas scheme.
#
# The paper reports ST1971. mlst uses the same seven-gene PubMLST scheme.
set -euo pipefail
cd "$(dirname "$0")/.."

THREADS="${THREADS:-16}"
FASTA="data/CP196749.1.fasta"
OUTDIR="results/mlst"
mkdir -p "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[mlst] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

echo "[mlst] typing with scheme paeruginosa ..."
mlst \
    --scheme paeruginosa \
    --full \
    --threads "$THREADS" \
    --nopath \
    "$FASTA" \
    > "$OUTDIR/mlst.tsv"

mlst --version > "$OUTDIR/mlst.version.txt"

ST="$(awk -F'\t' 'NR == 1 { for (i = 1; i <= NF; i++) col[$i] = i; next } { print $col["ST"] }' "$OUTDIR/mlst.tsv")"
SCHEME="$(awk -F'\t' 'NR == 1 { for (i = 1; i <= NF; i++) col[$i] = i; next } { print $col["SCHEME"] }' "$OUTDIR/mlst.tsv")"

cat "$OUTDIR/mlst.tsv"
printf 'scheme\t%s\nST\t%s\nexpected_ST\t1971\nstatus\t%s\n' \
    "$SCHEME" "$ST" "$([ "$ST" = 1971 ] && echo PASS || echo FAIL)" \
    > "$OUTDIR/mlst_check.tsv"

echo "[mlst] ST${ST} (expected 1971)"
if [ "$ST" != "1971" ]; then
    echo "[mlst] WARNING: ST does not match the paper" >&2
fi
