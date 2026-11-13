#!/usr/bin/env bash
# Step 3 - annotate the chromosome with Bakta, the tool used in the paper.
#
# Bakta needs a database. We keep it under db/ (git-ignored) so the download
# happens once and can be reused by later runs.
set -euo pipefail
cd "$(dirname "$0")/.."

THREADS="${THREADS:-16}"
FASTA="data/CP196749.1.fasta"
# The Bakta 1.10.3 "full" database is ~39 GB to download. The "light"
# database is ~1.5 GB and still provides the standard Bakta annotation; we
# deliberately run AMRFinderPlus, RGI and MLST as separate tools, so we do
# not need Bakta's bundled AMR/MLST databases. Set BAKTA_DB_TYPE=full only if
# you really want the extra cross-references.
DB_TYPE="${BAKTA_DB_TYPE:-light}"
DB="db/bakta-${DB_TYPE}"
OUTDIR="results/bakta"
PREFIX="strain71"

if [ ! -s "$FASTA" ]; then
    echo "[bakta] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

mkdir -p "$DB" "$OUTDIR"

if [ ! -s "$DB/version.json" ]; then
    echo "[bakta] downloading the $DB_TYPE Bakta database (first run only) ..."
    bakta_db download --output "$DB" --type "$DB_TYPE"
fi

echo "[bakta] annotating $FASTA with Bakta $(bakta --version 2>/dev/null | tail -n1) [$DB_TYPE DB] ..."
bakta \
    --db "$DB" \
    --output "$OUTDIR" \
    --prefix "$PREFIX" \
    --threads "$THREADS" \
    --force \
    "$FASTA" \
    > "$OUTDIR/bakta.stdout.log" 2> "$OUTDIR/bakta.stderr.log"

bakta --version > "$OUTDIR/bakta.version.txt"
grep -E '^(Software|Database|DOI|URL):' "$OUTDIR/bakta.stdout.log" > "$OUTDIR/bakta.run_info.txt" 2>/dev/null || true

echo "[bakta] output:"
ls -lh "$OUTDIR/${PREFIX}.faa" "$OUTDIR/${PREFIX}.ffn" "$OUTDIR/${PREFIX}.gff3" "$OUTDIR/${PREFIX}.tsv" "$OUTDIR/${PREFIX}.txt"
