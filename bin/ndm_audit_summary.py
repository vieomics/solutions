#!/usr/bin/env python3
"""Summarize a read-level blaNDM audit (see bin/ndm_read_audit.sh).

Usage: ndm_audit_summary.py <sample> <bam> <depth> [ref_offset]

Reference coordinates used for the LC928496 NDM-1 reference:
  CDS 268-1080; KP reported deletion (CDS 10-300) -> 278-568;
  PA reported deletion (CDS 794-813) -> 1061-1080.
"""
import re
import subprocess
import sys

sample, bam, depthfile = sys.argv[1:4]

dep = {}
for line in open(depthfile):
    _, p, d = line.split("\t")
    dep[int(p)] = int(d)


def mean(a, b):
    v = [dep.get(i, 0) for i in range(a, b + 1)]
    return sum(v) / len(v)


mapped = span5 = span3 = del5 = del3 = 0
out = subprocess.run(["samtools", "view", "-F", "4", bam], capture_output=True, text=True)
for line in out.stdout.splitlines():
    f = line.split("\t")
    pos = int(f[3])
    length = len(f[9])
    end = pos + length - 1
    cig = f[5]
    mapped += 1
    if pos <= 568 and end >= 278:
        span5 += 1
    if pos <= 1080 and end >= 1061:
        span3 += 1
    if "D" in cig:
        refpos = pos
        for ln, op in re.findall(r"(\d+)([MIDNSHP=X])", cig):
            ln = int(ln)
            if op in "MDN=X":
                if op == "D":
                    if not (refpos + ln < 278 or refpos > 568):
                        del5 += 1
                    if not (refpos + ln < 1061 or refpos > 1080):
                        del3 += 1
                refpos += ln

print("sample\tmapped\tCDS_mean\treg5p_mean\treg3p_mean\tspan_5p\tspan_3p\tdel_5p\tdel_3p")
print(
    f"{sample}\t{mapped}\t{mean(268, 1080):.0f}\t{mean(278, 568):.0f}\t"
    f"{mean(1061, 1080):.0f}\t{span5}\t{span3}\t{del5}\t{del3}"
)
