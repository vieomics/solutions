#!/usr/bin/env bash
# Run AMRFinderPlus on the 13 available ST1971 assemblies.
#
# The output is one TSV per genome under results/heatmap/amrfinder/. We use the
# nucleotide mode because the public assemblies do not all ship an annotation,
# and the paper's Fig. 1B is an acquired-ARG presence/copy-number heatmap.
set -euo pipefail
cd "$(dirname "$0")/../.."

MANIFEST="results/heatmap/genomes.tsv"
OUTDIR="results/heatmap/amrfinder"
DB="${AMRFINDER_DB:-db/amrfinder}"
THREADS="${THREADS:-8}"
mkdir -p "$OUTDIR"

if [ ! -s "$MANIFEST" ]; then
    echo "[amrfinder] ERROR: $MANIFEST is missing; run fetch_genomes.sh first" >&2
    exit 1
fi
if [ ! -s "$DB/version.txt" ]; then
    echo "[amrfinder] ERROR: AMRFinderPlus database missing; run bin/00_stage_databases.sh" >&2
    exit 1
fi

tail -n +2 "$MANIFEST" | while IFS=$'\t' read -r accession label country note assembly_dir fasta_gz md5; do
    out="$OUTDIR/${accession}.tsv"
    if [ -s "$out" ]; then
        echo "[amrfinder] $accession already done; skipping"
        continue
    fi
    echo "[amrfinder] $accession ($country)"
    amrfinder \
        --nucleotide "$fasta_gz" \
        --organism Pseudomonas_aeruginosa \
        --database "$DB" \
        --threads "$THREADS" \
        --output "$out" \
        > "$OUTDIR/${accession}.stdout.log" \
        2> "$OUTDIR/${accession}.stderr.log"
    echo "[amrfinder] $accession: $(($(wc -l < "$out") - 1)) rows"
done

echo "[amrfinder] done; outputs in $OUTDIR"
