#!/usr/bin/env bash
# Post-assembly analysis for the blaNDM truncation project.
#
# Runs, for one assembly:
#   1. AMRFinderPlus  -> AMR gene calls (contig locations)
#   2. MOB-suite      -> plasmid reconstruction / replicon typing
#   3. Kleborate      -> K. pneumoniae typing (ST, K/O, virulence, AMR) [optional]
#   4. IS context     -> IS26 / ISAba125 hits on the assembly
#   5. Co-location    -> are blaNDM and blaOXA-48 on the same contig?
#
# Usage:
#   pixi run -e analysis bash bin/assembly_analysis.sh <assembly.fasta> <sample_id> <outdir> [klebsiella]
set -euo pipefail
ASM="$1"; SAMPLE="$2"; OUT="$3"; SPECIES="${4:-}"
mkdir -p "$OUT"

# 1) AMR genes
amrfinder --nucleotide "$ASM" --output "$OUT/${SAMPLE}.amrfinder.tsv" >/dev/null

# 2) Plasmid reconstruction / typing
mob_recon --infile "$ASM" --outdir "$OUT/${SAMPLE}.mob_recon" --force >/dev/null 2>&1 || true

# 3) Species-specific typing
if [ "$SPECIES" = "klebsiella" ]; then
    kleborate -a "$ASM" -o "$OUT/${SAMPLE}.kleborate" --preset kpsc >/dev/null 2>&1 || true
fi

# 4) IS context (IS26 / ISAba125 extracted from ISfinder)
for is in IS26 ISAba125; do
    [ -f "analysis/test/isfinder/${is}.fna" ] || continue
    makeblastdb -in "$ASM" -dbtype nucl -out "$OUT/${SAMPLE}.asm_db" >/dev/null 2>&1
    blastn -query "analysis/test/isfinder/${is}.fna" -db "$OUT/${SAMPLE}.asm_db" \
        -outfmt "6 qseqid sseqid sstart send pident length" \
        > "$OUT/${SAMPLE}.${is}.tsv" 2>/dev/null || true
done

# 5) Co-location of blaNDM and blaOXA-48
python3 - "$OUT/${SAMPLE}.amrfinder.tsv" "$OUT/${SAMPLE}.colocation.txt" <<'PY'
import csv, sys
amr, out = sys.argv[1], sys.argv[2]
contigs = {}
with open(amr) as fh:
    for row in csv.DictReader(fh, delimiter='\t'):
        sym = row.get('Element symbol', '')
        if sym in ('blaNDM', 'blaOXA-48', 'blaOXA-48-like'):
            contigs.setdefault(sym, set()).add(row.get('Contig id'))
lines = [f"{k}: {sorted(v)}" for k, v in contigs.items()]
shared = contigs.get('blaNDM', set()) & (contigs.get('blaOXA-48', set()) | contigs.get('blaOXA-48-like', set()))
lines.append(f"same contig (blaNDM & blaOXA-48): {sorted(shared) if shared else 'none'}")
open(out, 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines))
PY

echo "done -> $OUT"
