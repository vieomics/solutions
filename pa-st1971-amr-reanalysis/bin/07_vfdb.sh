#!/usr/bin/env bash
# Step 7 - virulence-factor context with ABRicate + VFDB.
#
# The paper used VFDB through the VFinder web service. ABRicate uses the same
# VFDB nucleotide database locally, with explicit identity/coverage cut-offs.
set -euo pipefail
cd "$(dirname "$0")/.."

THREADS="${THREADS:-16}"
FASTA="data/CP196749.1.fasta"
OUTDIR="results/virulence"
mkdir -p "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[vfdb] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

# The databases ship with the package but must be formatted once.
abricate --setupdb > "$OUTDIR/abricate_setupdb.log" 2>&1

echo "[vfdb] screening with VFDB (ABRicate $(abricate --version 2>/dev/null | tail -n1)) ..."
abricate \
    --db vfdb \
    --minid 90 \
    --mincov 50 \
    --threads "$THREADS" \
    "$FASTA" \
    > "$OUTDIR/vfdb.tsv"

abricate --version > "$OUTDIR/abricate.version.txt"

echo "[vfdb] hits: $(($(wc -l < "$OUTDIR/vfdb.tsv") - 1))"
