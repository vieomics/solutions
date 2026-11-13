#!/usr/bin/env bash
# Step 1 - download the single public genome used in this solution.
#
# The paper (Nguyen et al., J Glob Antimicrob Resist 2026) deposited the
# complete chromosome as CP196749.1 / NZ_CP196749.1. Raw Illumina/Nanopore
# reads are not linked to the BioProject, so the reproducible AMR analysis
# starts from this finished assembly.
set -euo pipefail
cd "$(dirname "$0")/.."

ACCESSION="${ACCESSION:-CP196749.1}"
URL="https://www.ebi.ac.uk/ena/browser/api/fasta/${ACCESSION}"
OUT="data/${ACCESSION}.fasta"
EXPECTED_MD5="${EXPECTED_MD5:-0a70bcde2b23a14b74033a6da8078b24}"

mkdir -p data

if [ -s "$OUT" ] && printf '%s  %s\n' "$EXPECTED_MD5" "$OUT" | md5sum -c --status; then
    echo "[download] $OUT already present and checksum matches; skipping."
else
    echo "[download] fetching $ACCESSION from ENA ..."
    rm -f "$OUT.part"
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused "$URL" -o "$OUT.part"
    mv "$OUT.part" "$OUT"
fi

printf '%s  %s\n' "$EXPECTED_MD5" "$OUT" | md5sum -c -
echo "[download] md5 OK: $EXPECTED_MD5"

{
    echo "source: ENA browser API"
    echo "url: $URL"
    echo "accession: $ACCESSION"
    echo "refseq_accession: NZ_CP196749.1"
    echo "bioproject: PRJNA1285411"
    echo "biosample: SAMN49764163"
    echo "organism: Pseudomonas aeruginosa strain 71"
    echo "expected_md5: $EXPECTED_MD5"
    echo "downloaded_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "sha256: $(sha256sum "$OUT" | cut -d' ' -f1)"
    echo "note: raw reads are not available in SRA/ENA for this BioProject;"
    echo "      this finished chromosome is the public starting point."
} > data/download_info.txt

head -n 1 "$OUT"
echo "[download] wrote data/download_info.txt"
