#!/usr/bin/env python3
"""Step 9 - draw two beginner-friendly figures from the AMRFinderPlus table.

Input : results/amrfinder/amrfinder.tsv
Output: results/figures/amr_gene_map.png
        results/figures/amr_classes.png

The script uses only the Python standard library plus matplotlib. It reads the
same table a user can open in a spreadsheet; there is no hidden state.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

ROOT = Path(__file__).resolve().parent.parent
AMR_TSV = ROOT / "results" / "amrfinder" / "amrfinder.tsv"
QC_TSV = ROOT / "results" / "qc" / "seqkit_stats.tsv"
OUTDIR = ROOT / "results" / "figures"


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def genome_length() -> int:
    rows = read_tsv(QC_TSV)
    return int(float(rows[0]["sum_len"]))


def amr_hits() -> list[dict[str, str]]:
    """Keep one row per acquired AMR gene copy, not one row per database hit."""
    seen: set[tuple[str, str, str, str]] = set()
    hits: list[dict[str, str]] = []
    for row in read_tsv(AMR_TSV):
        # AMRFinderPlus 4.x uses "Type"/"Element symbol"; older tables use
        # "Element type"/"Gene symbol".
        if row.get("Type", row.get("Element type", "")) != "AMR":
            continue
        if row.get("Method", "").startswith("POINT"):
            continue
        gene = row.get("Element symbol", row.get("Gene symbol", "")).strip()
        if not gene:
            continue
        key = (
            gene,
            row.get("Contig id", ""),
            row.get("Start", ""),
            row.get("Stop", ""),
        )
        if key in seen:
            continue
        seen.add(key)
        hits.append(row)
    return hits


def class_color_map(hits: list[dict[str, str]]) -> dict[str, tuple]:
    classes = sorted({row.get("Class", "unclassified") for row in hits})
    cmap = plt.get_cmap("tab20")
    return {name: cmap(index % 20) for index, name in enumerate(classes)}


def plot_gene_map(hits: list[dict[str, str]], length: int, colors: dict[str, tuple]) -> None:
    if not hits:
        raise SystemExit("No AMR rows found in results/amrfinder/amrfinder.tsv")

    hits = sorted(hits, key=lambda row: int(row["Start"]))
    lanes = 6
    fig, ax = plt.subplots(figsize=(13, 6.2))
    ax.plot([0, length / 1e6], [0, 0], color="#222222", linewidth=2, zorder=1)

    for index, row in enumerate(hits):
        start, stop = int(row["Start"]), int(row["Stop"])
        midpoint = ((start + stop) / 2) / 1e6
        lane = index % lanes
        height = 0.45 + 0.38 * lane
        gene = row.get("Element symbol", row.get("Gene symbol", "?"))
        color = colors.get(row.get("Class", "unclassified"), (0.2, 0.2, 0.2, 1.0))
        is_tmex = gene.lower().startswith(("tmex", "toprj"))
        ax.plot([midpoint, midpoint], [0, height], color=color, linewidth=1.4, zorder=2)
        ax.scatter(
            midpoint, height, s=46 if is_tmex else 28,
            color=color, edgecolor="black" if is_tmex else "none",
            linewidth=0.8, zorder=3,
        )
        ax.text(
            midpoint, height + 0.10, gene,
            rotation=48, ha="left", va="bottom", fontsize=7.5,
            fontweight="bold" if is_tmex else "normal",
        )

    ax.set_xlim(0, length / 1e6)
    ax.set_ylim(-0.35, 2.95)
    ax.set_yticks([])
    ax.set_xlabel("Chromosome position (Mb)")
    ax.set_title(
        f"Acquired AMR genes on the {length / 1e6:.2f} Mb P. aeruginosa chromosome",
        loc="left", fontsize=12,
    )
    ax.spines[["top", "right", "left"]].set_visible(False)
    handles = [
        Line2D([0], [0], color=color, lw=3, label=name)
        for name, color in colors.items()
    ]
    ax.legend(
        handles=handles, title="Antibiotic class", frameon=False,
        loc="upper right", fontsize=7, title_fontsize=8, ncol=2,
    )
    fig.tight_layout()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTDIR / "amr_gene_map.png", dpi=300)
    plt.close(fig)


def plot_class_counts(hits: list[dict[str, str]]) -> None:
    counts: Counter[str] = Counter()
    for row in hits:
        for drug_class in row.get("Class", "unclassified").split("/"):
            counts[drug_class.strip() or "unclassified"] += 1
    labels, values = zip(*counts.most_common())
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.barh(range(len(labels)), values, color="#4c78a8")
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlabel("AMR gene copies")
    ax.set_title("Acquired AMR genes by antibiotic class", loc="left", fontsize=12)
    for index, value in enumerate(values):
        ax.text(value + 0.08, index, str(value), va="center", fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTDIR / "amr_classes.png", dpi=300)
    plt.close(fig)


def main() -> None:
    hits = amr_hits()
    length = genome_length()
    colors = class_color_map(hits)
    plot_gene_map(hits, length, colors)
    plot_class_counts(hits)
    print(f"[figures] {len(hits)} AMR gene copies, {len(colors)} antibiotic classes")
    print(f"[figures] wrote {OUTDIR / 'amr_gene_map.png'}")
    print(f"[figures] wrote {OUTDIR / 'amr_classes.png'}")


if __name__ == "__main__":
    main()
