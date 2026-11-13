#!/usr/bin/env bash
# Step 8 - turn the tool outputs into one small, readable summary.
#
# This is deliberately plain awk: no Python, no notebook, no parser library.
# It is also a template for reading the real output files yourself.
set -euo pipefail
cd "$(dirname "$0")/.."

OUT="results/summary.md"
TSV="results/summary.tsv"
mkdir -p results

genome_size="NA"
gc="NA"
num_seqs="NA"
if [ -s results/qc/seqkit_stats.tsv ]; then
    read -r num_seqs genome_size gc < <(
        awk -F'\t' '
            NR == 1 { for (i = 1; i <= NF; i++) col[$i] = i; next }
            { print $col["num_seqs"], $col["sum_len"], $col["GC(%)"] }
        ' results/qc/seqkit_stats.tsv
    )
fi

mlst_st="NA"
mlst_scheme="NA"
if [ -s results/mlst/mlst.tsv ]; then
    read -r mlst_scheme mlst_st < <(
        awk -F'\t' '
            NR == 1 { for (i = 1; i <= NF; i++) col[$i] = i; next }
            { print $col["SCHEME"], $col["ST"] }
        ' results/mlst/mlst.tsv
    )
fi

amr_count="NA"
if [ -s results/amrfinder/amrfinder.tsv ]; then
    amr_count="$(awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == "Gene symbol") gene = i
                if ($i == "Element type") type = i
            }
            next
        }
        gene && (type == 0 || $type == "AMR") && $gene != "" { seen[$gene] = 1 }
        END { n = 0; for (g in seen) n++; print n }
    ' results/amrfinder/amrfinder.tsv)"
fi

rgi_count="NA"
if [ -s results/rgi/strain71.txt ]; then
    rgi_count="$(awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) if ($i == "Best_Hit_ARO") gene = i
            next
        }
        gene && $gene != "" { seen[$gene] = 1 }
        END { n = 0; for (g in seen) n++; print n }
    ' results/rgi/strain71.txt)"
fi

vf_count="NA"
if [ -s results/virulence/vfdb.tsv ]; then
    vf_count="$(awk -F'\t' '
        NR == 1 { for (i = 1; i <= NF; i++) if ($i == "GENE") gene = i; next }
        gene && $gene != "" { seen[$gene] = 1 }
        END { n = 0; for (g in seen) n++; print n }
    ' results/virulence/vfdb.tsv)"
fi

tmex_hits="$(grep -riE 'tmexCD|toprJ' results/amrfinder results/rgi results/virulence 2>/dev/null | wc -l || true)"

{
    echo "# Pseudomonas aeruginosa strain 71 - AMR summary"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "## Genome"
    echo
    echo "| metric | value |"
    echo "|---|---|"
    echo "| sequences | $num_seqs |"
    echo "| length (bp) | $genome_size |"
    echo "| GC (%) | $gc |"
    echo
    echo "## Sequence type"
    echo
    echo "| scheme | ST |"
    echo "|---|---|"
    echo "| $mlst_scheme | $mlst_st |"
    echo
    echo "## AMRFinderPlus"
    echo
    echo "Unique AMR gene symbols: **$amr_count**"
    echo
    if [ -s results/amrfinder/amrfinder.tsv ]; then
        awk -F'\t' '
            NR == 1 {
                for (i = 1; i <= NF; i++) {
                    if ($i == "Gene symbol") gene = i
                    if ($i == "Class") class = i
                    if ($i == "Subclass") sub = i
                    if ($i == "Method") method = i
                    if ($i == "Element type") type = i
                }
                print "| gene | class | subclass | method |"
                print "|---|---|---|---|"
                next
            }
            gene && (type == 0 || $type == "AMR") && $gene != "" {
                key = $gene "|" $class "|" $sub "|" $method
                if (!seen[key]++) {
                    printf "| %s | %s | %s | %s |\n", $gene, $class, $sub, $method
                }
            }
        ' results/amrfinder/amrfinder.tsv
    else
        echo "_AMRFinderPlus output not found yet._"
    fi
    echo
    echo "Point-mutation report: \`results/amrfinder/point_mutations.tsv\`"
    echo
    echo "## CARD-RGI"
    echo
    echo "Unique best-hit ARO names: **$rgi_count**"
    echo
    if [ -s results/rgi/strain71.txt ]; then
        awk -F'\t' '
            NR == 1 {
                for (i = 1; i <= NF; i++) {
                    if ($i == "Best_Hit_ARO") gene = i
                    if ($i == "Cut_Off") cutoff = i
                    if ($i == "Best_Identities") ident = i
                    if ($i == "Drug Class") drug = i
                    if ($i == "Resistance Mechanism") mech = i
                }
                print "| gene | cut-off | identity (%) | drug class | mechanism |"
                print "|---|---|---|---|---|"
                next
            }
            gene && $gene != "" {
                key = $gene "|" $cutoff "|" $ident "|" $drug "|" $mech
                if (!seen[key]++) {
                    printf "| %s | %s | %s | %s | %s |\n", $gene, $cutoff, $ident, $drug, $mech
                }
            }
        ' results/rgi/strain71.txt
    else
        echo "_CARD-RGI output not found yet._"
    fi
    echo
    echo "## Virulence factors (VFDB via ABRicate)"
    echo
    echo "Unique VFDB genes: **$vf_count**"
    echo
    if [ -s results/virulence/vfdb.tsv ]; then
        awk -F'\t' '
            NR == 1 { for (i = 1; i <= NF; i++) if ($i == "GENE") gene = i; next }
            gene && $gene != "" { seen[$gene] = 1 }
            END { for (g in seen) print "- " g }
        ' results/virulence/vfdb.tsv | sort
    else
        echo "_VFDB output not found yet._"
    fi
    echo
    echo "## tmexCD2-toprJ2"
    echo
    if [ "$tmex_hits" -gt 0 ]; then
        echo "Detected in at least one result file:"
        echo '```text'
        grep -riE 'tmexCD|toprJ' results/amrfinder results/rgi results/virulence 2>/dev/null | head -n 20 || true
        echo '```'
    else
        echo "_No tmexCD/toprJ match found yet (or the relevant step has not finished)._"
    fi
} > "$OUT"

{
    printf 'metric\tvalue\n'
    printf 'genome_length_bp\t%s\n' "$genome_size"
    printf 'gc_percent\t%s\n' "$gc"
    printf 'mlst_scheme\t%s\n' "$mlst_scheme"
    printf 'mlst_ST\t%s\n' "$mlst_st"
    printf 'amrfinder_unique_genes\t%s\n' "$amr_count"
    printf 'rgi_unique_genes\t%s\n' "$rgi_count"
    printf 'vfdb_unique_genes\t%s\n' "$vf_count"
    printf 'tmex_toprJ_matches\t%s\n' "$tmex_hits"
} > "$TSV"

echo "[summary] wrote $OUT and $TSV"
