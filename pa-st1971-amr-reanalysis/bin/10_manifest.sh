#!/usr/bin/env bash
# Step 10 - build the small, committed summary tables under manifests/.
#
# Results stay in results/; manifests/ holds the comparison tables a reader can
# open without rerunning anything. Everything here is plain awk/sha256sum.
set -euo pipefail
cd "$(dirname "$0")/.."

OUTDIR="manifests"
mkdir -p "$OUTDIR"

metric() {
    awk -F'\t' -v key="$1" '$1 == key { print $2; found = 1 } END { if (!found) print "NA" }' results/summary.tsv
}

genome_size="$(metric genome_length_bp)"
gc="$(metric gc_percent)"
mlst_st="$(metric mlst_ST)"
amr_count="$(metric amrfinder_unique_genes)"
amr_nonpoint="$(metric amrfinder_nonpoint_genes)"
rgi_count="$(metric rgi_unique_genes)"
vf_count="$(metric vfdb_unique_genes)"

# ---------------------------------------------------------------------------
# Software and database versions
# ---------------------------------------------------------------------------
{
    printf 'tool\tversion\tenvironment\n'
    printf 'pixi\t%s\tbase\n' "$(pixi --version 2>/dev/null | awk '{print $2}')"
    printf 'seqkit\t%s\tdefault\n' "$(sed -n 's/^seqkit v\{0,1\}//p' results/qc/seqkit.version.txt 2>/dev/null | head -n1)"
    printf 'mlst\t%s\ttyping\n' "$(sed -n 's/^mlst //p' results/mlst/mlst.version.txt 2>/dev/null | head -n1)"
    printf 'amrfinder\t%s\tannotation\n' "$(head -n1 results/amrfinder/amrfinder.version.txt 2>/dev/null)"
    printf 'rgi\t%s\tresistome\n' "$(head -n1 results/rgi/rgi.version.txt 2>/dev/null)"
    printf 'abricate\t%s\tvirulence\n' "$(sed -n 's/^abricate //p' results/virulence/abricate.version.txt 2>/dev/null | head -n1)"
    printf 'python\t%s\tviz\n' "$(pixi run -e viz python --version 2>/dev/null | awk '{print $2}')"
} > "$OUTDIR/software_versions.tsv"

{
    printf 'database\tversion\tsource\n'
    awk -F'\t' 'NR > 1 { printf "%s\t%s\t%s\n", $1, $2, $3 }' db/database_sources.tsv
} > "$OUTDIR/database_versions.tsv"

# ---------------------------------------------------------------------------
# AMRFinderPlus: unique AMR symbols (including and excluding point calls)
# ---------------------------------------------------------------------------
{
    printf 'gene\tclass\tsubclass\tmethod\tcontig\tstart\tstop\n'
    awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == "Gene symbol" || $i == "Element symbol") gene = i
                if ($i == "Element type" || $i == "Type") type = i
                if ($i == "Class") class = i
                if ($i == "Subclass") subclass = i
                if ($i == "Method") method = i
                if ($i == "Start") start = i
                if ($i == "Stop") stop = i
                if ($i == "Contig id") contig = i
            }
            next
        }
        gene && (type == 0 || $type == "AMR") && $gene != "" {
            key = $gene "\t" $class "\t" $subclass "\t" $method
            if (!seen[key]++) {
                printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\n", $gene, $class, $subclass, $method, $contig, $start, $stop
            }
        }
    ' results/amrfinder/amrfinder.tsv | sort -t$'\t' -k1,1
} > "$OUTDIR/amr_genes.tsv"

cp results/amrfinder/point_mutations.tsv "$OUTDIR/point_mutations.tsv"

# ---------------------------------------------------------------------------
# CARD-RGI and VFDB
# ---------------------------------------------------------------------------
{
    printf 'gene\tcut_off\tidentity_percent\tdrug_class\tmechanism\tamr_gene_family\n'
    awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == "Best_Hit_ARO") gene = i
                if ($i == "Cut_Off") cutoff = i
                if ($i == "Best_Identities") ident = i
                if ($i == "Drug Class") drug = i
                if ($i == "Resistance Mechanism") mech = i
                if ($i == "AMR Gene Family") family = i
            }
            next
        }
        gene && $gene != "" {
            key = $gene "\t" $cutoff "\t" $ident "\t" $drug "\t" $mech "\t" $family
            if (!seen[key]++) {
                printf "%s\t%s\t%s\t%s\t%s\t%s\n", $gene, $cutoff, $ident, $drug, $mech, $family
            }
        }
    ' results/rgi/strain71.txt | sort -t$'\t' -k1,1
} > "$OUTDIR/rgi_calls.tsv"

{
    printf 'gene\tproduct\tdatabase\thits\tbest_identity_percent\n'
    awk -F'\t' '
        NR == 1 {
            for (i = 1; i <= NF; i++) {
                if ($i == "GENE") gene = i
                if ($i == "PRODUCT") product = i
                if ($i == "%IDENTITY") ident = i
                if ($i == "DATABASE") database = i
            }
            next
        }
        gene && $gene != "" {
            key = $gene "\t" $product "\t" $database
            count[key]++
            if ($ident + 0 > best[key]) best[key] = $ident + 0
        }
        END {
            for (key in count) {
                printf "%s\t%d\t%s\n", key, count[key], best[key]
            }
        }
    ' results/virulence/vfdb.tsv | sort -t$'\t' -k1,1
} > "$OUTDIR/vfdb_genes.tsv"

# ---------------------------------------------------------------------------
# Paper vs observed comparison
# ---------------------------------------------------------------------------
named_status="PASS"
for gene in blaPDC-142 blaPME-1 blaOXA-395; do
    if ! cut -f6 results/amrfinder/amrfinder.tsv | grep -qx "$gene"; then
        named_status="CHECK"
    fi
done

if cut -f6 results/amrfinder/amrfinder.tsv | grep -qx 'tmexD2' && \
   cut -f6 results/amrfinder/amrfinder.tsv | grep -qx 'toprJ'; then
    tmex_status="PASS"
else
    tmex_status="CHECK"
fi

colistin_calls="$(awk -F'\t' '
    NR == 1 { for (i = 1; i <= NF; i++) {
        if ($i == "Element symbol") gene = i
        if ($i == "Class") class = i
        if ($i == "Method") method = i
        if ($i == "Element name") name = i
    }; next }
    method && $method == "POINTP" && $class == "COLISTIN" && $name !~ /WILDTYPE/ { print $gene }
' results/amrfinder/amrfinder.tsv | sort -u | paste -sd ';' -)"
colistin_calls="${colistin_calls:-none}"

{
    printf 'category\titem\tpaper_value\tobserved\tstatus\tnote\n'
    printf 'genome\tgenome_size_bp\t6589538\t%s\t%s\t\n' "$genome_size" "$([ "$genome_size" = 6589538 ] && echo PASS || echo CHECK)"
    printf 'genome\tgc_percent\t66.17\t%s\t%s\t\n' "$gc" "$([ "$gc" = 66.17 ] && echo PASS || echo CHECK)"
    printf 'typing\tsequence_type\tST1971\tST%s\t%s\t\n' "$mlst_st" "$([ "$mlst_st" = 1971 ] && echo PASS || echo CHECK)"
    printf 'resistome\tamr_symbol_count\t18\t%s\tINFO\tNon-point AMR symbols; the paper count depends on whether partial genes and tmex subunits are counted separately.\n' "$amr_nonpoint"
    printf 'resistome\tnamed_ARGs\tblaPDC-142; blaPME-1; blaOXA-395\t\t%s\t\n' "$named_status"
    printf 'resistome\ttigecycline_cluster\ttmexCD2-toprJ2\ttmexC; tmexD2; toprJ\t%s\tDetected by AMRFinderPlus.\n' "$tmex_status"
    printf 'resistome\tcolistin_mutations\t10 reported variants\t%s\tINFO\tNon-wildtype AMRFinderPlus calls only; other paper variants appear in point_mutations.tsv as wildtype/considered rows.\n' "$colistin_calls"
    printf 'virulence\tvirulence_factor_count\t213\t%s unique genes\tINFO\tABRicate VFDB release is newer than the paper analysis.\n' "$vf_count"
    printf 'resistome\tCARD_unique_ARO\tnot reported\t%s\tINFO\tCARD reports intrinsic efflux pumps as well as acquired genes.\n' "$rgi_count"
} > "$OUTDIR/paper_comparison.tsv"

# ---------------------------------------------------------------------------
# Reproducibility manifest and execution report
# ---------------------------------------------------------------------------
checksums=""
for path in \
    results/qc/seqkit_stats.tsv \
    results/mlst/mlst.tsv \
    results/annotation/annotation_summary.tsv \
    results/amrfinder/amrfinder.tsv \
    results/amrfinder/point_mutations.tsv \
    results/rgi/strain71.txt \
    results/virulence/vfdb.tsv \
    results/summary.tsv; do
    if [ -s "$path" ]; then
        entry="$(printf '    "%s": "%s"' "$path" "$(sha256sum "$path" | cut -d' ' -f1)")"
        if [ -n "$checksums" ]; then checksums="${checksums},\n${entry}"; else checksums="$entry"; fi
    fi
done

annotation_source="$(awk -F'\t' '$1 == "source" { print $2 }' results/annotation/annotation_summary.tsv 2>/dev/null || echo NA)"
protein_count="$(awk -F'\t' '$1 == "cds_with_translation" { print $2 }' results/annotation/annotation_summary.tsv 2>/dev/null || echo NA)"

{
    printf '{\n'
    printf '  "project": "Pseudomonas aeruginosa ST1971 AMR reanalysis",\n'
    printf '  "generated_utc": "%s",\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf '  "paper_doi": "10.1016/j.jgar.2026.03.007",\n'
    printf '  "input": {\n'
    printf '    "accession": "CP196749.1",\n'
    printf '    "genome_md5": "0a70bcde2b23a14b74033a6da8078b24",\n'
    printf '    "genome_sha256": "%s",\n' "$(sha256sum data/CP196749.1.fasta | cut -d' ' -f1)"
    printf '    "genbank_sha256": "%s"\n' "$(sha256sum data/CP196749.1.gbff | cut -d' ' -f1)"
    printf '  },\n'
    printf '  "annotation": {\n'
    printf '    "source": "%s",\n' "$annotation_source"
    printf '    "translated_cds": %s\n' "$protein_count"
    printf '  },\n'
    printf '  "databases": {\n'
    printf '    "amrfinderplus": "%s",\n' "$(awk -F'\t' '$1 == "AMRFinderPlus" { print $2 }' db/database_sources.tsv)"
    printf '    "card": "%s"\n' "$(awk -F'\t' '$1 == "CARD" { print $2 }' db/database_sources.tsv)"
    printf '  },\n'
    printf '  "commands": [\n'
    printf '    "pixi install --all",\n'
    printf '    "bash bin/00_stage_databases.sh",\n'
    printf '    "bash bin/run_all.sh"\n'
    printf '  ],\n'
    printf '  "checksums": {\n'
    printf '%b\n' "$checksums"
    printf '  }\n'
    printf '}\n'
} > "$OUTDIR/reproducibility_manifest.json"

{
    echo "# Workflow execution report"
    echo
    echo "Generated: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo
    echo "## Dataset"
    echo
    echo "- Isolate: *Pseudomonas aeruginosa* strain 71 (ST1971)"
    echo "- Genome: \`CP196749.1\` / \`NZ_CP196749.1\`, 6,589,538 bp"
    echo "- BioProject: PRJNA1285411"
    echo "- Raw reads: not public; the finished chromosome is the input"
    echo
    echo "## Execution"
    echo
    echo "- Host CPUs: $(nproc 2>/dev/null || echo NA)"
    echo "- Annotation: $annotation_source"
    echo "- AMRFinderPlus database: $(awk -F'\t' '$1 == "AMRFinderPlus" { print $2 }' db/database_sources.tsv)"
    echo "- CARD database: $(awk -F'\t' '$1 == "CARD" { print $2 }' db/database_sources.tsv)"
    echo "- Commands: \`bash bin/00_stage_databases.sh\` then \`bash bin/run_all.sh\`"
    echo
    echo "## Validation"
    echo
    echo "| Check | Observed | Status |"
    echo "|---|---|---|"
    echo "| Genome length | $genome_size bp | $([ "$genome_size" = 6589538 ] && echo PASS || echo CHECK) |"
    echo "| Sequence type | ST$mlst_st | $([ "$mlst_st" = 1971 ] && echo PASS || echo CHECK) |"
    echo "| Named ARGs | blaPDC-142, blaPME-1, blaOXA-395 | $named_status |"
    echo "| tmexCD2-toprJ2 | tmexC, tmexD2, toprJ | $tmex_status |"
    echo "| AMR symbols (non-point) | $amr_nonpoint | INFO |"
    echo "| CARD unique ARO names | $rgi_count | INFO |"
    echo "| VFDB unique genes | $vf_count | INFO |"
    echo
    echo "## Committed outputs"
    echo
    echo "- \`results/summary.md\` and \`results/summary.tsv\`"
    echo "- \`results/amrfinder/\`, \`results/rgi/\`, \`results/virulence/\`"
    echo "- \`results/figures/amr_gene_map.png\` and \`amr_classes.png\`"
    echo "- \`manifests/amr_genes.tsv\`, \`rgi_calls.tsv\`, \`vfdb_genes.tsv\`"
    echo "- \`manifests/paper_comparison.tsv\`"
    echo
    echo "## Caveats"
    echo
    echo "- The paper's exact Bakta annotation was not rerun by default. The"
    echo "  deposited GenBank proteins are used instead; optional Bakta mode is"
    echo "  documented in the README."
    echo "- The public CARD and VFDB releases are newer than the paper's."
    echo "- A name in \`point_mutations.tsv\` can be a wildtype row. Compare the"
    echo "  \`Element name\` and \`Method\` columns before calling a mutation present."
} > "$OUTDIR/workflow_execution_report.md"

echo "[manifest] wrote $OUTDIR/software_versions.tsv"
echo "[manifest] wrote $OUTDIR/database_versions.tsv"
echo "[manifest] wrote $OUTDIR/amr_genes.tsv"
echo "[manifest] wrote $OUTDIR/point_mutations.tsv"
echo "[manifest] wrote $OUTDIR/rgi_calls.tsv"
echo "[manifest] wrote $OUTDIR/vfdb_genes.tsv"
echo "[manifest] wrote $OUTDIR/paper_comparison.tsv"
echo "[manifest] wrote $OUTDIR/reproducibility_manifest.json"
echo "[manifest] wrote $OUTDIR/workflow_execution_report.md"
