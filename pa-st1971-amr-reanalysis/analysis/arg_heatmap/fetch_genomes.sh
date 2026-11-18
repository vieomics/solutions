#!/usr/bin/env bash
# Fetch the 13 ST1971 genomes that are publicly available as assemblies.
#
# The paper compared strain 71 with 24 public ST1971 genomes (Fig. 1B). Twelve
# of those are deposited only as raw reads (SRR...), so they need assembly
# first. The other twelve public genomes, plus strain 71 itself, are available
# as GCA assemblies. This script fetches those 13 genomes from the NCBI FTP
# mirror and records their provenance.
set -euo pipefail
cd "$(dirname "$0")/../.."

OUTDIR="results/heatmap"
GNMDIR="data/public_genomes"
mkdir -p "$OUTDIR" "$GNMDIR"

# accession | label | country | note
GENOMES=(
    "GCA_043498125|GCA_043498125|Greece|public assembly"
    "GCA_035818655|GCA_035818655|China|public assembly"
    "GCA_051905005|strain 71|Vietnam|this study (paper row GCA_051905005)"
    "GCA_011683115|GCA_011683115|China|public assembly"
    "GCA_011683045|GCA_011683045|China|public assembly"
    "GCA_001721845|GCA_001721845|China|public assembly"
    "GCA_001722045|GCA_001722045|China|public assembly"
    "GCA_001721745|GCA_001721745|China|public assembly"
    "GCA_001721805|GCA_001721805|China|public assembly"
    "GCA_001721765|GCA_001721765|China|public assembly"
    "GCA_001722025|GCA_001722025|China|public assembly"
    "GCA_001721825|GCA_001721825|China|public assembly"
    "GCA_001721785|GCA_001721785|China|public assembly"
)

{
    printf 'accession\tlabel\tcountry\tnote\tassembly_dir\tfasta_gz\tmd5\n'
} > "$OUTDIR/genomes.tsv"

for entry in "${GENOMES[@]}"; do
    IFS='|' read -r accession label country note <<< "$entry"
    digits="${accession#GCA_}"
    parent_url="https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/${digits:0:3}/${digits:3:3}/${digits:6:3}/"

    echo "[fetch] $accession ($country)"
    assembly_dir="$(curl -fsSL --retry 3 --retry-delay 5 --connect-timeout 20 --max-time 120 \
        "$parent_url" \
        | grep -oE 'href="GCA_[0-9]+\.[0-9]+_[^"]+/"' \
        | sed 's/^href="//; s/"$//' \
        | head -n1)"

    if [ -z "$assembly_dir" ]; then
        echo "[fetch] ERROR: cannot resolve assembly directory for $accession" >&2
        exit 1
    fi

    assembly_url="${parent_url}${assembly_dir}"
    filename="$(curl -fsSL --retry 3 --retry-delay 5 --connect-timeout 20 --max-time 120 \
        "$assembly_url" \
        | grep -oE 'href="[^"]+_genomic.fna.gz"' \
        | grep -vE '_cds_from_|_rna_from_' \
        | sed 's/^href="//; s/"$//' \
        | head -n1)"

    if [ -z "$filename" ]; then
        echo "[fetch] ERROR: no genomic FASTA in $assembly_url" >&2
        exit 1
    fi

    out="$GNMDIR/${accession}.fna.gz"
    url="${assembly_url}${filename}"
    if [ ! -s "$out" ] || ! gzip -t "$out" 2>/dev/null; then
        echo "[fetch] downloading $filename"
        rm -f "$out"
        curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused \
            --connect-timeout 20 --max-time 600 \
            "$url" -o "$out"
    else
        echo "[fetch] cached $out"
    fi

    if ! gzip -t "$out" 2>/dev/null; then
        echo "[fetch] ERROR: $out is not a valid gzip file" >&2
        exit 1
    fi

    md5="$(md5sum "$out" | cut -d' ' -f1)"
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\n' \
        "$accession" "$label" "$country" "$note" "$assembly_dir" "$out" "$md5" \
        >> "$OUTDIR/genomes.tsv"
    echo "[fetch] $accession OK ($(du -h "$out" | cut -f1))"
done

echo "[fetch] wrote $OUTDIR/genomes.tsv"
