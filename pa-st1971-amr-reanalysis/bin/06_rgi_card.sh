#!/usr/bin/env bash
# Step 6 - CARD-RGI, the second ARG caller used in the paper.
#
# CARD data is downloaded from card.mcmaster.ca and loaded into a local
# database (./localDB) so RGI does not need write access to the conda prefix.
set -euo pipefail
cd "$(dirname "$0")/.."

THREADS="${THREADS:-16}"
# RGI 6.0.3 rejects more than 8 threads, even on larger machines.
RGI_THREADS=$(( THREADS > 8 ? 8 : THREADS ))
FASTA="data/CP196749.1.fasta"
CARD_DIR="${CARD_DB:-db/card}"
CARD_TAR="$CARD_DIR/card-data.tar.bz2"
OUTDIR="results/rgi"
mkdir -p "$CARD_DIR" "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[rgi] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

if [ ! -s "$CARD_DIR/card.json" ]; then
    echo "[rgi] downloading the CARD database (first run only) ..."
    rm -f "$CARD_TAR"
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused \
        https://card.mcmaster.ca/latest/data -o "$CARD_TAR"
    tar -xjf "$CARD_TAR" -C "$CARD_DIR"
fi

echo "[rgi] loading CARD into ./localDB ..."
rgi load --card_json "$CARD_DIR/card.json" --local > "$OUTDIR/rgi_load.log" 2>&1

echo "[rgi] running CARD-RGI $(rgi main --version 2>/dev/null | tail -n1) ..."
rm -f "$OUTDIR/strain71.txt" "$OUTDIR/strain71.json"
rgi main \
    --input_sequence "$FASTA" \
    --output_file "$OUTDIR/strain71" \
    --input_type contig \
    --num_threads "$RGI_THREADS" \
    --local \
    --clean \
    > "$OUTDIR/rgi_main.stdout.log" 2> "$OUTDIR/rgi_main.stderr.log"

rgi main --version > "$OUTDIR/rgi.version.txt"

echo "[rgi] output:"
ls -lh "$OUTDIR/strain71.txt" "$OUTDIR/strain71.json"
