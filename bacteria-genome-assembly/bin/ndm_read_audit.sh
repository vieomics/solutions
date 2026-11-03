#!/usr/bin/env bash
# Read-level audit of blaNDM integrity (H1-H4 test).
#
# Maps reads against a full-length NDM reference and reports:
#   - mapped reads
#   - mean depth over the CDS and over the two reported deletion regions
#     (KP: CDS 10-300 -> ref 278-568; PA: CDS 794-813 -> ref 1061-1080)
#   - reads spanning each deletion region
#   - reads carrying a deletion overlapping each region
#
# Usage:
#   bash bin/ndm_read_audit.sh <sample_id> <R1> <R2> <ndm_ref.fasta> <outdir>
set -euo pipefail
SAMPLE="$1"; R1="$2"; R2="$3"; REF="$4"; OUT="$5"
mkdir -p "$OUT"

if [ ! -f "${REF}.bwt" ]; then bwa index "$REF" >/dev/null 2>&1; fi

bwa mem -t 8 "$REF" "$R1" "$R2" 2>/dev/null | samtools sort -@ 4 -o "$OUT/${SAMPLE}.bam"
samtools index "$OUT/${SAMPLE}.bam"
samtools depth -a "$OUT/${SAMPLE}.bam" > "$OUT/${SAMPLE}.depth"

python3 - "$SAMPLE" "$OUT/${SAMPLE}.bam" "$OUT/${SAMPLE}.depth" <<'PY'
import sys, re, subprocess
sample, bam, depthfile = sys.argv[1:4]

dep = {}
for line in open(depthfile):
    _, p, d = line.split('\t')
    dep[int(p)] = int(d)

def mean(a, b):
    v = [dep.get(i, 0) for i in range(a, b + 1)]
    return sum(v) / len(v)

mapped = span5 = span3 = del5 = del3 = 0
out = subprocess.run(['samtools', 'view', '-F', '4', bam], capture_output=True, text=True)
for line in out.stdout.splitlines():
    f = line.split('\t')
    pos = int(f[3]); L = len(f[9]); end = pos + L - 1; cig = f[5]
    mapped += 1
    if pos <= 568 and end >= 278:
        span5 += 1
    if pos <= 1080 and end >= 1061:
        span3 += 1
    if 'D' in cig:
        refpos = pos
        for ln, op in re.findall(r'(\d+)([MIDNSHP=X])', cig):
            ln = int(ln)
            if op in 'MDN=X':
                if op == 'D':
                    if not (refpos + ln < 278 or refpos > 568):
                        del5 += 1
                    if not (refpos + ln < 1061 or refpos > 1080):
                        del3 += 1
                refpos += ln

print(f"{sample}\tmapped={mapped}\tCDS={mean(268,1080):.0f}x\t5'reg(278-568)={mean(278,568):.0f}x\t3'reg(1061-1080)={mean(1061,1080):.0f}x\tspan5'={span5}\tspan3'={span3}\tdel5'={del5}\tdel3'={del3}")
PY
