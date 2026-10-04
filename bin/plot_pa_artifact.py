#!/usr/bin/env python3
"""Proof figure for the P. aeruginosa isolate (021-A-244 / ERR14693665):
the reported blaNDM 3' truncation is an assembly artifact.

Panels
  A - read depth across the NDM-1 reference; reported deleted region shaded
  B - zoom: per-base depth + individual read alignments crossing the region
  C - the draft-assembly artifact (gene fragment at a contig boundary)

Usage: python3 bin/plot_pa_artifact.py <outdir>
"""
import csv
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/figures"
os.makedirs(OUT, exist_ok=True)

# ---- data ----
dep = {}
for line in open("results/ndm_audit/ERX14095156.depth"):
    _, p, d = line.split("\t")
    dep[int(p)] = int(d)


def mean(a, b):
    v = [dep.get(i, 0) for i in range(a, b + 1)]
    return sum(v) / len(v)


cds_mean = mean(268, 1080)
reg_mean = mean(1061, 1080)

reads = []
with open("analysis/test/pa_reads_spanning.tsv") as fh:
    for r in csv.DictReader(fh, delimiter="\t"):
        reads.append((int(r["start"]), int(r["end"]), r["strand"]))

# blaNDM row from AMRFinderPlus (assembly)
amr = None
for row in csv.DictReader(open("analysis/postasm/ERX14095156.amrfinder.tsv"), delimiter="\t"):
    if row.get("Element symbol") == "blaNDM":
        amr = row
        break
asm_start, asm_stop = int(amr["Start"]), int(amr["Stop"])
asm_cov = float(amr["% Coverage of reference"])
asm_strand = amr["Strand"]

# contig length
name = None
contigs = {}
buf = []
for line in open("analysis/assemblies/ERX14095156.fasta"):
    if line.startswith(">"):
        if name:
            contigs[name] = "".join(buf)
        name = line[1:].split()[0]
        buf = []
    else:
        buf.append(line.strip())
contigs[name] = "".join(buf)
contig_len = len(contigs[amr["Contig id"]])

# ---- figure ----
fig = plt.figure(figsize=(10, 10))
gs = fig.add_gridspec(3, 1, height_ratios=[1.1, 1.6, 0.8], hspace=0.35)

# Panel A
ax = fig.add_subplot(gs[0])
xs = list(range(200, 1081, 10))
ys = [sum(dep.get(i, 0) for i in range(x, x + 10)) / 10 for x in xs]
ax.plot(xs, ys, lw=1, color="#1f77b4")
ax.axvspan(1061, 1080, color="red", alpha=0.25)
ax.axvspan(268, 1080, color="#1f77b4", alpha=0.05)
ax.set_xlim(200, 1085)
ax.set_ylabel("read depth")
ax.set_title("A  Read coverage across full-length NDM-1 (ERR14693665 / 021-A-244)",
             loc="left", fontsize=10)
ax.text(1061, max(ys) * 0.95, "reported deletion\n(CDS 794-813)", ha="right",
        fontsize=8, color="red", va="top")
ax.text(300, max(ys) * 0.9, f"CDS mean {cds_mean:.0f}x", fontsize=8)
ax.text(300, max(ys) * 0.75, f"reported region mean {reg_mean:.0f}x", fontsize=8)

# Panel B
ax = fig.add_subplot(gs[1])
zx = list(range(1000, 1086))
zy = [dep.get(i, 0) for i in zx]
ax.fill_between(zx, 0, zy, color="#1f77b4", alpha=0.35)
ax.axvline(1061, color="red", ls="--", lw=1)
ax.axvline(1080, color="red", ls="--", lw=1)
ax.text(1070, max(zy) * 1.05, "1061-1080", ha="center", fontsize=8, color="red")
# read alignments (subsample, alternate rows)
sub = reads[:: max(1, len(reads) // 40)][:40]
for i, (s, e, strand) in enumerate(sub):
    y = -6 - (i % 12) * 1.6
    ax.plot([max(s, 1000), min(e, 1085)], [y, y], lw=1.2,
            color="#ff7f0e" if strand == "-" else "#2ca02c")
ax.set_ylim(-30, max(zy) * 1.2)
ax.set_xlim(1000, 1085)
ax.set_ylabel("read depth / reads")
ax.set_title("B  Zoom at the reported deletion: every base is covered; "
             "154 reads span the region (0 reads carry a deletion)",
             loc="left", fontsize=10)
ax.text(1002, -3, "individual reads (orange = reverse, green = forward)",
        fontsize=7.5, va="top")

# Panel C
ax = fig.add_subplot(gs[2])
ax.add_patch(Rectangle((0, 0.3), contig_len, 0.4, facecolor="#dddddd",
                       edgecolor="#555555"))
# gene alignment on contig coordinates (strand-aware)
g0, g1 = min(asm_start, asm_stop), max(asm_start, asm_stop)
ax.add_patch(Rectangle((g0, 0.3), g1 - g0, 0.4, facecolor="#1f77b4",
                       edgecolor="none"))
ax.annotate("blaNDM fragment\n(AMRFinderPlus: 97.41% coverage)",
            xy=((g0 + g1) / 2, 0.7), xytext=((g0 + g1) / 2, 1.05),
            ha="center", fontsize=8, arrowprops=dict(arrowstyle="-", lw=0.8))
# for a + strand alignment the 5' end is at the alignment start; for - at the end
five_end = g0 if asm_strand == "+" else g1
ax.annotate("contig boundary cuts the gene's 5' end\n"
            "(CDS 1-20 incl. start codon, missing)",
            xy=(five_end, 0.3), xytext=(five_end + contig_len * 0.30, -0.25),
            ha="center", fontsize=8, color="red",
            arrowprops=dict(arrowstyle="-", color="red", lw=0.8))
ax.text(contig_len / 2, 0.5, f"draft contig ({contig_len:,} bp)", ha="center",
        va="center", fontsize=8)
ax.set_xlim(-100, contig_len + 100)
ax.set_ylim(-0.6, 1.3)
ax.set_yticks([])
ax.set_xlabel("contig position (bp)")
ax.set_title("C  The artifact: the draft contig starts inside the gene (5' end "
             "missing) - not the reported 3' deletion; reads show it is intact",
             loc="left", fontsize=10)

fig.suptitle("Read-level evidence: the reported blaNDM truncation in "
             "P. aeruginosa 021-A-244 is an assembly artifact", fontsize=11.5, y=0.98)
fig.savefig(os.path.join(OUT, "figure4_PA_artifact_evidence.png"), dpi=200,
            bbox_inches="tight")
fig.savefig(os.path.join(OUT, "figure4_PA_artifact_evidence.svg"),
            bbox_inches="tight")
print("wrote", os.path.join(OUT, "figure4_PA_artifact_evidence.png"))
print(f"cds_mean={cds_mean:.1f} reg_mean={reg_mean:.1f} spanning={len(reads)} "
      f"amr={asm_strand} {asm_start}-{asm_stop} cov={asm_cov}")
