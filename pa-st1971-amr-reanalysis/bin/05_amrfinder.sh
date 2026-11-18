#!/usr/bin/env bash
# Step 5 - AMRFinderPlus, the paper's primary ARG/mutation caller.
#
# We run it twice:
#   amrfinder.tsv       core AMR report (used for the 18-ARG comparison)
#   amrfinder_plus.tsv  adds the "plus" stress/virulence genes (context only)
#
# The point-mutation report is written separately because AMRFinderPlus uses
# a different table for that information.
set -euo pipefail
cd "$(dirname "$0")/.."

THREADS="${THREADS:-16}"
FASTA="data/CP196749.1.fasta"
PROTEINS="results/annotation/strain71.faa"
GFF="results/annotation/strain71.gff3"
DB="${AMRFINDER_DB:-db/amrfinder}"
OUTDIR="results/amrfinder"
mkdir -p "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[amrfinder] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi
if [ ! -s "$PROTEINS" ] || [ ! -s "$GFF" ]; then
    echo "[amrfinder] ERROR: annotation is missing; run bin/03_annotate.sh first" >&2
    exit 1
fi

# The conda package does not ship the database. Prefer the copy staged from
# the public OmicsLab workspace (bin/00_stage_databases.sh); otherwise fetch
# it once from NCBI into db/ so a pixi reinstall does not lose it.
if [ ! -s "$DB/version.txt" ]; then
    echo "[amrfinder] downloading the AMRFinderPlus database (first run only) ..."
    amrfinder_update --database "$DB" --force_update
fi

DB_VERSION="$(amrfinder --database "$DB" --database_version 2>/dev/null | tail -n1)"
echo "[amrfinder] database: $DB_VERSION"

COMMON=(
    --nucleotide "$FASTA"
    --protein "$PROTEINS"
    --gff "$GFF"
    --organism Pseudomonas_aeruginosa
    --database "$DB"
    --mutation_all "$OUTDIR/point_mutations.tsv"
    --threads "$THREADS"
)

echo "[amrfinder] running core AMR report ..."
amrfinder "${COMMON[@]}" --output "$OUTDIR/amrfinder.tsv"

echo "[amrfinder] running plus-gene report ..."
amrfinder "${COMMON[@]}" --plus --output "$OUTDIR/amrfinder_plus.tsv"

amrfinder --version > "$OUTDIR/amrfinder.version.txt"
printf '%s\n' "$DB_VERSION" > "$OUTDIR/amrfinder.database_version.txt"

echo "[amrfinder] core hits: $(($(wc -l < "$OUTDIR/amrfinder.tsv") - 1))"
echo "[amrfinder] point-mutation rows: $(($(wc -l < "$OUTDIR/point_mutations.tsv") - 1))"
