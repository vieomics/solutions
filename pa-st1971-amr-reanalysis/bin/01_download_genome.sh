#!/usr/bin/env bash
# Step 1 - download the single public genome used in this solution.
#
# The paper (Nguyen et al., J Glob Antimicrob Resist 2026) deposited the
# complete chromosome as CP196749.1 / NZ_CP196749.1. Raw Illumina/Nanopore
# reads are not linked to the BioProject, so the reproducible AMR analysis
# starts from this finished assembly.
#
# Two public mirrors serve the same record. NCBI is tried first because it is
# usually available when the EBI browser API is slow or blocked; ENA is the
# fallback. Both must produce the same MD5, so the checksum - not the mirror -
# is what the rest of the workflow trusts.
set -euo pipefail
cd "$(dirname "$0")/.."

ACCESSION="${ACCESSION:-CP196749.1}"
OUT="data/${ACCESSION}.fasta"
EXPECTED_MD5="${EXPECTED_MD5:-0a70bcde2b23a14b74033a6da8078b24}"

mkdir -p data

if [ -s "$OUT" ] && printf '%s  %s\n' "$EXPECTED_MD5" "$OUT" | md5sum -c --status; then
    echo "[download] $OUT already present and checksum matches; skipping."
    SOURCE_NAME="existing file"
    SOURCE_URL="(local file was already verified)"
else
    # Ordered mirrors. Keep the accession in the URL so the provenance is clear.
    SOURCE_NAMES=("NCBI E-utilities" "ENA browser API")
    SOURCE_URLS=(
        "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=${ACCESSION}&rettype=fasta&retmode=text"
        "https://www.ebi.ac.uk/ena/browser/api/fasta/${ACCESSION}"
    )

    SOURCE_NAME=""
    SOURCE_URL=""
    for i in "${!SOURCE_URLS[@]}"; do
        url="${SOURCE_URLS[$i]}"
        name="${SOURCE_NAMES[$i]}"
        echo "[download] fetching $ACCESSION from $name ..."
        rm -f "$OUT.part"
        if curl -fsSL --retry 3 --retry-delay 5 --retry-connrefused \
                --connect-timeout 20 --max-time 600 "$url" -o "$OUT.part" \
            && printf '%s  %s\n' "$EXPECTED_MD5" "$OUT.part" | md5sum -c --status; then
            mv "$OUT.part" "$OUT"
            SOURCE_NAME="$name"
            SOURCE_URL="$url"
            break
        fi
        echo "[download] $name failed or returned the wrong checksum; trying next mirror." >&2
        rm -f "$OUT.part"
    done

    if [ ! -s "$OUT" ]; then
        echo "[download] ERROR: no mirror returned a valid $ACCESSION fasta." >&2
        echo "[download] Check your network, then rerun this script." >&2
        exit 1
    fi
fi

printf '%s  %s\n' "$EXPECTED_MD5" "$OUT" | md5sum -c -
echo "[download] md5 OK: $EXPECTED_MD5"

# The GenBank flat file carries the authors' CDS coordinates and translations.
# Step 3 uses it to build the protein FASTA and GFF3 that AMRFinderPlus needs.
GBFF="data/${ACCESSION}.gbff"
GBFF_URL="https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=nuccore&id=${ACCESSION}&rettype=gbwithparts&retmode=text"
if [ -s "$GBFF" ] && grep -q "^VERSION" "$GBFF"; then
    echo "[download] $GBFF already present; skipping."
else
    echo "[download] fetching the annotated GenBank record ..."
    rm -f "$GBFF.part"
    curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused \
        --connect-timeout 20 --max-time 600 "$GBFF_URL" -o "$GBFF.part"
    mv "$GBFF.part" "$GBFF"
fi
if ! grep -q "^VERSION" "$GBFF"; then
    echo "[download] ERROR: $GBFF is not a valid GenBank flat file." >&2
    exit 1
fi

{
    echo "source: $SOURCE_NAME"
    echo "url: $SOURCE_URL"
    echo "genbank_url: $GBFF_URL"
    echo "accession: $ACCESSION"
    echo "refseq_accession: NZ_CP196749.1"
    echo "bioproject: PRJNA1285411"
    echo "biosample: SAMN49764163"
    echo "organism: Pseudomonas aeruginosa strain 71"
    echo "expected_md5: $EXPECTED_MD5"
    echo "downloaded_utc: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "sha256: $(sha256sum "$OUT" | cut -d' ' -f1)"
    echo "genbank_sha256: $(sha256sum "$GBFF" | cut -d' ' -f1)"
    echo "note: raw reads are not available in SRA/ENA for this BioProject;"
    echo "      this finished chromosome is the public starting point."
} > data/download_info.txt

head -n 1 "$OUT"
echo "[download] wrote data/download_info.txt"
