#!/usr/bin/env python3
"""Assay map (Figure 3): ref-29 NDM amplicon vs the two deletion regions.

Usage: python3 bin/plot_assay.py <outdir>
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/figures"
os.makedirs(OUT, exist_ok=True)

# reference LC928496: CDS 268-1080; amplicon ref 841-953 (CDS 574-686)
CDS0, CDS1 = 1, 813
AMP0, AMP1 = 574, 686          # CDS coordinates of the 113 bp amplicon
KP_DEL = (10, 300)             # reported KP deletion (CDS)
PA_DEL = (794, 813)            # reported PA deletion (CDS)
F_PRIMER = (574, 593)
R_PRIMER = (668, 686)

fig, ax = plt.subplots(figsize=(10, 2.6))
ax.add_patch(Rectangle((CDS0, 0), CDS1 - CDS0, 0.5, facecolor="#dbe9f6", edgecolor="#1f77b4"))
ax.add_patch(Rectangle((AMP0, 0), AMP1 - AMP0, 0.5, facecolor="#1f77b4", edgecolor="none"))
ax.add_patch(Rectangle((KP_DEL[0], -0.45), KP_DEL[1] - KP_DEL[0], 0.35, facecolor="orange", alpha=0.8))
ax.add_patch(Rectangle((PA_DEL[0], -0.45), PA_DEL[1] - PA_DEL[0], 0.35, facecolor="red", alpha=0.8))
for x0, x1, lab in [(F_PRIMER[0], F_PRIMER[1], "NDM-F"), (R_PRIMER[0], R_PRIMER[1], "NDM-R")]:
    ax.add_patch(Rectangle((x0, 0.5), x1 - x0, 0.12, facecolor="black"))
    ax.text((x0 + x1) / 2, 0.72, lab, ha="center", fontsize=7)
ax.text((AMP0 + AMP1) / 2, 0.22, "113 bp amplicon\n(intact in all alleles)", ha="center", va="center",
        fontsize=8, color="white")
ax.text((KP_DEL[0] + KP_DEL[1]) / 2, -0.62, "reported KP deletion (CDS 10-300)", ha="center", fontsize=7.5)
ax.text((PA_DEL[0] + PA_DEL[1]) / 2, -0.62, "reported PA\ndeletion", ha="center", fontsize=7.5)
ax.set_xlim(-20, 860)
ax.set_ylim(-0.9, 0.95)
ax.set_yticks([])
ax.set_xlabel("blaNDM-1 CDS position (bp)")
ax.set_title("The deployed NDM PCR amplicon lies outside both reported deletion regions", fontsize=11)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "figure3_assay_map.png"), dpi=200)
fig.savefig(os.path.join(OUT, "figure3_assay_map.svg"))
print("wrote", os.path.join(OUT, "figure3_assay_map.png"))
