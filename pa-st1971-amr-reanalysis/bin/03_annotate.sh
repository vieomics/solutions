#!/usr/bin/env bash
# Step 3 - prepare the protein FASTA and GFF3 used by AMRFinderPlus.
#
# Default (ANNOTATION_SOURCE=genbank):
#   Reuse the authors' deposited GenBank annotation. This is fast, needs no
#   database download, and produces the same two files AMRFinderPlus needs.
#
# Optional (ANNOTATION_SOURCE=bakta):
#   Reproduce the paper's Bakta 1.10.3 annotation. This downloads the Bakta
#   light database (~1.5 GB) on first use.
set -euo pipefail
cd "$(dirname "$0")/.."

SOURCE="${ANNOTATION_SOURCE:-genbank}"
THREADS="${THREADS:-16}"
FASTA="data/CP196749.1.fasta"
OUTDIR="results/annotation"
mkdir -p "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[annotation] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

case "$SOURCE" in
    genbank)
        echo "[annotation] using the deposited GenBank annotation (no database download) ..."
        python bin/03_prepare_annotation.py
        ;;
    bakta)
        DB_TYPE="${BAKTA_DB_TYPE:-light}"
        DB="db/bakta-${DB_TYPE}"
        PREFIX="strain71"
        BAKTA_OUT="results/bakta"
        mkdir -p "$DB" "$BAKTA_OUT"

        if [ ! -s "$DB/version.json" ]; then
            echo "[annotation] downloading the $DB_TYPE Bakta database (first run only) ..."
            bakta_db download --output "$DB" --type "$DB_TYPE"
        fi

        echo "[annotation] running Bakta $(bakta --version 2>/dev/null | tail -n1) [$DB_TYPE DB] ..."
        bakta \
            --db "$DB" \
            --output "$BAKTA_OUT" \
            --prefix "$PREFIX" \
            --threads "$THREADS" \
            --force \
            "$FASTA" \
            > "$BAKTA_OUT/bakta.stdout.log" 2> "$BAKTA_OUT/bakta.stderr.log"

        bakta --version > "$BAKTA_OUT/bakta.version.txt"
        grep -E '^(Software|Database|DOI|URL):' "$BAKTA_OUT/bakta.stdout.log" \
            > "$BAKTA_OUT/bakta.run_info.txt" 2>/dev/null || true

        cp "$BAKTA_OUT/${PREFIX}.faa" "$OUTDIR/strain71.faa"
        cp "$BAKTA_OUT/${PREFIX}.gff3" "$OUTDIR/strain71.gff3"
        {
            printf 'metric\tvalue\n'
            printf 'source\tBakta %s (%s database)\n' "$(cat "$BAKTA_OUT/bakta.version.txt")" "$DB_TYPE"
            printf 'protein_fasta\t%s\n' "$OUTDIR/strain71.faa"
            printf 'gff3\t%s\n' "$OUTDIR/strain71.gff3"
        } > "$OUTDIR/annotation_summary.tsv"
        ;;
    *)
        echo "[annotation] ERROR: ANNOTATION_SOURCE must be 'genbank' or 'bakta'." >&2
        exit 1
        ;;
esac

echo "[annotation] source: $SOURCE"
echo "[annotation] proteins: $OUTDIR/strain71.faa"
echo "[annotation] GFF3:     $OUTDIR/strain71.gff3"
