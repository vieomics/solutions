#!/usr/bin/env python3
"""Junction structure schematic (Figure 2).

Shows, per isolate, which part of the blaNDM CDS is present (blue), deleted
(grey), and the IS26/ISAba125 element joined at the 5' junction.

Usage: python3 bin/plot_junctions.py <outdir>
"""
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

OUT = sys.argv[1] if len(sys.argv) > 1 else "docs/figures"
os.makedirs(OUT, exist_ok=True)

# isolate, junction CDS position (1-based, first present base), upstream element, label
ROWS = [
    ("03-A-063", 318, "IS26", "K. pneumoniae - real 5' deletion"),
    ("03-A-038", 318, "IS26", "K. pneumoniae - real 5' deletion"),
    ("11-A-427", 266, "IS26", "K. pneumoniae - real 5' deletion"),
    ("24-A-028", 10, "IS26", "K. pneumoniae - start codon lost"),
    ("021-A-244", 1, "ISAba125", "P. aeruginosa - intact (reported deletion = artifact)"),
]
CDS_START, CDS_END = 1, 813

fig, ax = plt.subplots(figsize=(10, 5))
for i, (iso, junc, elem, label) in enumerate(ROWS):
    y = len(ROWS) - i
    # deleted portion
    if junc > CDS_START:
        ax.add_patch(Rectangle((CDS_START, y - 0.18), junc - CDS_START, 0.36,
                               facecolor="#cccccc", edgecolor="none"))
    # present portion
    ax.add_patch(Rectangle((junc, y - 0.18), CDS_END - junc, 0.36,
                           facecolor="#1f77b4", edgecolor="none"))
    # upstream element
    ax.add_patch(Rectangle((CDS_START - 95, y - 0.18), 90, 0.36,
                           facecolor="#ff7f0e" if elem == "IS26" else "#2ca02c",
                           edgecolor="none"))
    ax.text(CDS_START - 100, y, elem, ha="right", va="center", fontsize=8,
            color="#ff7f0e" if elem == "IS26" else "#2ca02c")
    ax.text(CDS_END + 15, y, f"{iso}: {label}", ha="left", va="center", fontsize=9)
    if junc > CDS_START:
        ax.plot([junc], [y + 0.28], marker="v", color="black", ms=5)
        ax.text(junc, y + 0.42, f"junction CDS {junc}", ha="center", fontsize=7)

ax.axvline(1, color="black", lw=1)
ax.axvline(813, color="black", lw=1)
ax.text(1, 0.3, "ATG", ha="center", fontsize=7)
ax.text(813, 0.3, "stop", ha="center", fontsize=7)
ax.set_xlim(-180, 1150)
ax.set_ylim(0.3, len(ROWS) + 1.1)
ax.set_yticks([])
ax.set_xlabel("blaNDM-1 CDS position (bp)")
ax.set_title("blaNDM truncation structure: shared IS26 junctions vs intact gene", fontsize=11)
handles = [
    Rectangle((0, 0), 1, 1, facecolor="#1f77b4", label="present CDS"),
    Rectangle((0, 0), 1, 1, facecolor="#cccccc", label="deleted"),
    Rectangle((0, 0), 1, 1, facecolor="#ff7f0e", label="IS26 (upstream)"),
    Rectangle((0, 0), 1, 1, facecolor="#2ca02c", label="ISAba125 (upstream)"),
]
ax.legend(handles=handles, loc="lower right", fontsize=8, ncol=2)
fig.tight_layout()
fig.savefig(os.path.join(OUT, "figure2_junctions.png"), dpi=200)
fig.savefig(os.path.join(OUT, "figure2_junctions.svg"))
print("wrote", os.path.join(OUT, "figure2_junctions.png"))
