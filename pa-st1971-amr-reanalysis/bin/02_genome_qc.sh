#!/usr/bin/env bash
# Step 2 - check the downloaded FASTA before wasting time on annotation.
#
# This catches the common "I downloaded an HTML error page" problem and
# verifies that we have the expected 6,589,538 bp single chromosome.
set -euo pipefail
cd "$(dirname "$0")/.."

FASTA="data/CP196749.1.fasta"
EXPECTED_LENGTH="${EXPECTED_LENGTH:-6589538}"
OUTDIR="results/qc"
mkdir -p "$OUTDIR"

if [ ! -s "$FASTA" ]; then
    echo "[qc] ERROR: $FASTA is missing; run bin/01_download_genome.sh first" >&2
    exit 1
fi

seqkit stats -a -T "$FASTA" > "$OUTDIR/seqkit_stats.tsv"
seqkit stats -a "$FASTA" > "$OUTDIR/seqkit_stats.txt"

# Pull values by column name so this keeps working if seqkit reorders columns.
read -r NUM_SEQS SUM_LEN GC SUM_GAP < <(
    awk -F'\t' '
        NR == 1 { for (i = 1; i <= NF; i++) col[$i] = i; next }
        { print $col["num_seqs"], $col["sum_len"], $col["GC(%)"], $col["sum_gap"] }
    ' "$OUTDIR/seqkit_stats.tsv"
)

status="PASS"
if [ "$NUM_SEQS" != "1" ]; then status="FAIL"; fi
if [ "$SUM_LEN" != "$EXPECTED_LENGTH" ]; then status="FAIL"; fi

{
    printf 'check\texpected\tobserved\tstatus\n'
    printf 'number_of_sequences\t1\t%s\t%s\n' "$NUM_SEQS" "$([ "$NUM_SEQS" = 1 ] && echo PASS || echo FAIL)"
    printf 'genome_length_bp\t%s\t%s\t%s\n' "$EXPECTED_LENGTH" "$SUM_LEN" "$([ "$SUM_LEN" = "$EXPECTED_LENGTH" ] && echo PASS || echo FAIL)"
    printf 'gaps\t0\t%s\t%s\n' "$SUM_GAP" "$([ "$SUM_GAP" = 0 ] && echo PASS || echo FAIL)"
    printf 'gc_percent\t66.17\t%s\tINFO\n' "$GC"
} > "$OUTDIR/genome_check.tsv"

cat "$OUTDIR/genome_check.tsv"
echo "[qc] $status"

if [ "$status" != "PASS" ]; then
    echo "[qc] ERROR: downloaded genome does not match the paper." >&2
    exit 1
fi
