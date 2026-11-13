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
PROTEINS="results/bakta/strain71.faa"
DB="db/amrfinder"
OUTDIR="results/amrfinder"
mkdir -p "$DB" "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[amrfinder] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi
if [ ! -s "$PROTEINS" ]; then
    echo "[amrfinder] ERROR: $PROTEINS is missing; run bin/03_annotate.sh first" >&2
    exit 1
fi

# The conda package does not ship the database. Download it once into db/
# instead of writing inside .pixi/ so a reinstall does not lose it.
if [ ! -e "$DB/latest" ]; then
    echo "[amrfinder] downloading the AMRFinderPlus database (first run only) ..."
    amrfinder_update --database "$DB" --force_update
fi

DB_VERSION="$(amrfinder --database "$DB" --database_version 2>/dev/null | tail -n1)"
echo "[amrfinder] database: $DB_VERSION"

COMMON=(
    --nucleotide "$FASTA"
    --protein "$PROTEINS"
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
