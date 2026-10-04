#!/usr/bin/env python3
"""Coverage profiles across the NDM-1 reference for the 5 isolates (Figure 1).

Reads results/ndm_audit/<sample>.depth and plots mean depth in 20-bp windows,
shading the two reported deletion regions (CDS 10-300 -> ref 278-568;
CDS 794-813 -> ref 1061-1080).

Usage: python3 bin/plot_coverage.py <outdir>
"""
import glob
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/figures"
os.makedirs(OUT, exist_ok=True)

LABELS = {
    "ERX14095152": "03-A-063 (K. pneumoniae) - truncated",
    "ERX14095153": "03-A-038 (K. pneumoniae) - truncated",
    "ERX14095154": "24-A-028 (K. pneumoniae) - start codon lost",
    "ERX14095155": "11-A-427 (K. pneumoniae) - truncated",
    "ERX14095156": "021-A-244 (P. aeruginosa) - intact (artifact)",
}

fig, axes = plt.subplots(5, 1, figsize=(9, 11), sharex=True)
for ax, (sample, label) in zip(axes, LABELS.items()):
    path = f"results/ndm_audit/{sample}.depth"
    dep = {}
    for line in open(path):
        _, p, d = line.split("\t")
        dep[int(p)] = int(d)
    xs = list(range(1, 1081, 20))
    ys = []
    for x in xs:
        vals = [dep.get(i, 0) for i in range(x, x + 20)]
        ys.append(sum(vals) / len(vals))
    ax.plot(xs, ys, lw=1, color="#1f77b4")
    ax.axvspan(278, 568, color="orange", alpha=0.15)
    ax.axvspan(1061, 1080, color="red", alpha=0.15)
    ax.set_ylabel("depth")
    ax.set_title(label, fontsize=10, loc="left")
    ax.set_xlim(1, 1080)
axes[-1].set_xlabel("NDM-1 reference position (LC928496; CDS 268-1080)")
axes[0].legend(
    handles=[
        plt.Line2D([], [], color="#1f77b4", label="read depth"),
        plt.Rectangle((0, 0), 1, 1, color="orange", alpha=0.4, label="reported KP deletion (CDS 10-300)"),
        plt.Rectangle((0, 0), 1, 1, color="red", alpha=0.4, label="reported PA deletion (CDS 794-813)"),
    ],
    loc="upper right",
    fontsize=8,
)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "figure1_coverage_profiles.png"), dpi=200)
fig.savefig(os.path.join(OUT, "figure1_coverage_profiles.svg"))
print("wrote", os.path.join(OUT, "figure1_coverage_profiles.png"))
