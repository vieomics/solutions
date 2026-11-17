#!/usr/bin/env python3
"""Generate the publication-style figures for the HBV analysis."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from Bio import Phylo

GENOTYPE_COLORS = {
    "A": "#1f77b4",
    "B": "#ff7f0e",
    "C": "#d62728",
    "D": "#2ca02c",
    "E": "#9467bd",
    "F": "#8c564b",
    "G": "#e377c2",
    "H": "#7f7f7f",
    "I": "#bcbd22",
    "J": "#17becf",
}
REGIONS = {
    "S": (157, 837),
    "P": (2309, 3182, 1, 1625),
    "C": (1816, 2454),
    "X": (1376, 1840),
    "preS1": (2850, 3173),
    "preS2": (3174, 3182, 1, 156),
}


def read_tsv(path: Path) -> list[dict]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sample_labels(metadata_path: Path) -> dict[str, str]:
    labels = {}
    for row in read_tsv(metadata_path):
        ident = row["id"]
        if row["record_type"] == "study_consensus":
            alias = row.get("isolate", "").replace("_", "/")
            labels[ident] = f"{alias} (this study)"
        else:
            raw_date = row.get("collection_date", "")
            year = raw_date[:4] if raw_date and raw_date[:4].isdigit() else ""
            country = row["country"].replace("_", " ")
            if year:
                labels[ident] = f"{row['accession']} ({country}, {year})"
            elif country and country != "not available":
                labels[ident] = f"{row['accession']} ({country})"
            else:
                labels[ident] = f"{row['accession']} (RefSeq)"
    return labels


def plot_coverage(results: Path, outdir: Path, labels: dict[str, str]) -> None:
    samples = sorted(path.name.split(".depth.tsv")[0] for path in (results / "consensus").glob("*.depth.tsv"))
    if not samples:
        return
    fig, axes = plt.subplots(len(samples), 1, figsize=(11, 2.4 * len(samples)), sharex=True)
    if len(samples) == 1:
        axes = [axes]
    for ax, sample in zip(axes, samples):
        rows = read_tsv(results / "consensus" / f"{sample}.depth.tsv")
        positions = np.array([int(row["position"]) for row in rows])
        depths = np.array([int(row["depth"]) for row in rows])
        coverage = {
            row["metric"]: row["value"]
            for row in read_tsv(results / "consensus" / f"{sample}.coverage.tsv")
        }
        ax.fill_between(positions, 1, depths, color="#4c78a8", linewidth=0, alpha=0.85)
        low = depths < 10
        ax.fill_between(positions, 1, np.where(low, depths, 0), color="#d62728", linewidth=0, alpha=0.9)
        ax.set_yscale("symlog", linthresh=10)
        ax.set_ylim(0.8, max(depths.max() * 1.3, 100))
        ax.set_ylabel("Depth (×)")
        alias = labels.get(sample, sample)
        ax.set_title(
            f"{alias}  |  mean {float(coverage.get('mean_depth', 0)):.0f}×  |  "
            f"≥10× breadth {coverage.get('breadth_10x_pct', 'NA')}%  |  "
            f"N {coverage.get('final_n_bases', 'NA')}",
            loc="left",
            fontsize=10,
        )
        ax.grid(axis="x", color="#dddddd", linewidth=0.5, alpha=0.7)
        ax.spines[["top", "right"]].set_visible(False)
    axes[-1].set_xlabel("HBV genome position (NC_003977.2, 1-based)")
    axes[-1].set_xlim(1, 3182)
    # Individual genome maps are provided in hbv_genome_structure.png.
    fig.tight_layout()
    fig.savefig(outdir / "genome_coverage.png", dpi=300)
    plt.close(fig)


def _segments(coords: tuple[int, ...]) -> list[tuple[int, int]]:
    if len(coords) == 2:
        return [(coords[0], coords[1])]
    return [(coords[0], coords[1]), (coords[2], coords[3])]


def plot_qc(results: Path, outdir: Path, labels: dict[str, str]) -> None:
    samples = sorted(path.name.replace(".fastp.json", "") for path in (results / "trimmed").glob("*.fastp.json"))
    if not samples:
        return
    before, after, q30_before, q30_after, dup = [], [], [], [], []
    for sample in samples:
        data = json.loads((results / "trimmed" / f"{sample}.fastp.json").read_text())
        before.append(data["summary"]["before_filtering"]["total_reads"] / 1e6)
        after.append(data["summary"]["after_filtering"]["total_reads"] / 1e6)
        q30_before.append(data["summary"]["before_filtering"]["q30_rate"] * 100)
        q30_after.append(data["summary"]["after_filtering"]["q30_rate"] * 100)
        dup.append(data["duplication"]["rate"] * 100)
    x = np.arange(len(samples))
    fig, axes = plt.subplots(1, 3, figsize=(13, 4.2))
    axes[0].bar(x - 0.2, before, 0.4, label="raw", color="#9ecae1")
    axes[0].bar(x + 0.2, after, 0.4, label="trimmed", color="#3182bd")
    axes[0].set_ylabel("Reads (millions)")
    axes[0].set_title("Reads before / after fastp")
    axes[0].legend(frameon=False)
    axes[1].bar(x - 0.2, q30_before, 0.4, label="raw", color="#c7e9c0")
    axes[1].bar(x + 0.2, q30_after, 0.4, label="trimmed", color="#41ab5d")
    axes[1].set_ylabel("Q30 (%)")
    axes[1].set_ylim(80, 100)
    axes[1].set_title("Q30 before / after trimming")
    axes[2].bar(x, dup, 0.55, color="#e6550d")
    axes[2].set_ylabel("Duplication rate (%)")
    axes[2].set_title("Sequence duplication after trimming")
    aliases = [labels.get(sample, sample).split(" (")[0] for sample in samples]
    for ax in axes:
        ax.set_xticks(x)
        ax.set_xticklabels(aliases, rotation=30, ha="right")
        ax.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "qc_summary.png", dpi=300)
    plt.close(fig)


def _tree_layout(tree) -> tuple[dict, dict, float]:
    x_coords, y_coords = {}, {}
    terminals = tree.get_terminals()
    for index, terminal in enumerate(terminals):
        y_coords[id(terminal)] = index

    def assign(clade, x):
        x_coords[id(clade)] = x
        if clade.is_terminal():
            return
        children = clade.clades
        for child in children:
            assign(child, x + (child.branch_length or 0.0))
        y_coords[id(clade)] = (y_coords[id(children[0])] + y_coords[id(children[-1])]) / 2

    assign(tree.root, 0.0)
    max_x = max(x_coords.values()) if x_coords else 1.0
    return x_coords, y_coords, max_x


def plot_tree(tree_path: Path, metadata_path: Path, outdir: Path, labels: dict[str, str]) -> None:
    tree = Phylo.read(tree_path, "newick")
    tree.ladderize()
    x_coords, y_coords, max_x = _tree_layout(tree)
    meta = {row["id"]: row for row in read_tsv(metadata_path)}

    fig, ax = plt.subplots(figsize=(11.5, 0.45 * len(tree.get_terminals()) + 2.2))
    parent_map = {}
    def build_parent_map(node):
        for child in node.clades:
            parent_map[id(child)] = node
            build_parent_map(child)
    build_parent_map(tree.root)
    for clade in tree.find_clades(order="postorder"):
        if clade is tree.root:
            continue
        parent = parent_map[id(clade)]
        x0, x1 = x_coords[id(parent)], x_coords[id(clade)]
        y = y_coords[id(clade)]
        descendants = [terminal.name.split("|")[0] for terminal in clade.get_terminals()]
        genotypes = {meta.get(ident, {}).get("genotype", "NA") for ident in descendants}
        color = GENOTYPE_COLORS.get(next(iter(genotypes)), "#333333") if len(genotypes) == 1 else "#777777"
        ax.plot([x0, x1], [y, y], color=color, linewidth=1.4)
        if not clade.is_terminal():
            children_y = [y_coords[id(child)] for child in clade.clades]
            ax.plot([x1, x1], [min(children_y), max(children_y)], color=color, linewidth=1.0)
            support = clade.name or ""
            if support and support not in {"Root"}:
                ax.text(x1 + max_x * 0.002, y + 0.12, support, fontsize=6.5, color="#444444", va="bottom")

    for index, terminal in enumerate(tree.get_terminals()):
        ident = terminal.name.split("|")[0]
        genotype = meta.get(ident, {}).get("genotype", "NA")
        label = labels.get(ident, terminal.name)
        ax.text(max_x * 1.01, index, label, va="center", fontsize=8.2,
                color=GENOTYPE_COLORS.get(genotype, "#333333"),
                fontweight="bold" if meta.get(ident, {}).get("record_type") == "study_consensus" else "normal")
    ax.set_xlim(-max_x * 0.01, max_x * 1.38)
    ax.set_ylim(-0.8, len(tree.get_terminals()) - 0.2)
    ax.set_yticks([])
    ax.set_xlabel("Substitutions per site")
    ax.spines[["top", "right", "left"]].set_visible(False)
    scale = 0.02 if max_x > 0.08 else 0.01
    ax.plot([0, scale], [-0.6, -0.6], color="black", linewidth=2)
    ax.text(scale / 2, -0.45, f"{scale:.2f}", ha="center", fontsize=7)
    handles = [
        plt.Line2D([0], [0], color=color, lw=3, label=genotype)
        for genotype, color in GENOTYPE_COLORS.items()
        if any(row["genotype"] == genotype for row in meta.values())
    ]
    ax.legend(handles=handles, title="Genotype", frameon=False, loc="lower right", fontsize=7, title_fontsize=8)
    fig.tight_layout()
    fig.savefig(outdir / "phylogenetic_tree.png", dpi=300)
    plt.close(fig)


def _arrow(ax, start: int, end: int, y: float, height: float, color: str, label: str) -> None:
    from matplotlib.patches import FancyArrow

    ax.add_patch(
        FancyArrow(
            start, y, end - start, 0, width=height, head_width=height * 2.0,
            head_length=min(90, max(40, (end - start) * 0.06)), length_includes_head=True,
            color=color, alpha=0.9,
        )
    )
    ax.text((start + end) / 2, y + height * 1.6, label, ha="center", va="bottom", fontsize=9, fontweight="bold")


def plot_genome_structure(outdir: Path) -> None:
    fig, ax = plt.subplots(figsize=(11, 3.6))
    ax.set_xlim(0, 3182)
    ax.set_ylim(0, 1.0)
    ax.axhline(0.12, color="#333333", linewidth=1.2)
    ax.text(5, 0.06, "origin", fontsize=7, color="#666666")
    ax.text(3178, 0.06, "origin", fontsize=7, color="#666666", ha="right")
    _arrow(ax, 157, 837, 0.24, 0.05, "#f2c14e", "S")
    _arrow(ax, 1376, 1840, 0.40, 0.05, "#82b366", "X")
    _arrow(ax, 1816, 2454, 0.56, 0.05, "#d79b00", "C")
    # P spans the origin: draw the two genomic segments and connect them.
    _arrow(ax, 2309, 3182, 0.72, 0.05, "#6c8ebf", "")
    _arrow(ax, 1, 1625, 0.72, 0.05, "#6c8ebf", "")
    ax.text(1590, 0.86, "P (polymerase; spans origin)", ha="center", fontsize=9, fontweight="bold", color="#6c8ebf")
    ax.plot([3100, 3140, 3140], [0.72, 0.72, 0.80], color="#6c8ebf", linewidth=1)
    ax.plot([30, 30, 1], [0.80, 1.00, 1.00], color="#6c8ebf", linewidth=1, linestyle="--")
    # preS subregions
    ax.plot([2850, 3173], [0.18, 0.18], color="#8c6d31", linewidth=3)
    ax.text(3010, 0.19, "preS1", ha="center", fontsize=7, color="#8c6d31")
    ax.plot([3174, 3182], [0.18, 0.18], color="#8c6d31", linewidth=3)
    ax.plot([1, 156], [0.18, 0.18], color="#8c6d31", linewidth=3)
    ax.text(80, 0.19, "preS2", ha="center", fontsize=7, color="#8c6d31")
    ax.set_yticks([])
    ax.set_xlabel("HBV genome position (NC_003977.2, 1-based)")
    ax.spines[["top", "right", "left"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "hbv_genome_structure.png", dpi=300)
    plt.close(fig)


def plot_mutations(results: Path, outdir: Path, labels: dict[str, str]) -> None:
    summary = read_tsv(results / "variants" / "mutation_summary.tsv")
    samples = sorted({row["sample"] for row in summary})
    regions = ["S", "P", "C", "X"]
    matrix = np.zeros((len(samples), len(regions)), dtype=int)
    for row in summary:
        if row["region"] in regions and row["effect"] != "intergenic":
            matrix[samples.index(row["sample"]), regions.index(row["region"])] += int(row["count"])

    effects = read_tsv(results / "variants" / "amino_acid_variants.tsv")
    effect_types = ["synonymous", "nonsynonymous", "stop_gained", "uncertain"]
    effect_counts = {sample: Counter() for sample in samples}
    for row in effects:
        effect_counts[row["sample"]][row["effect"]] += 1

    fig, axes = plt.subplots(1, 3, figsize=(14, 4.5), gridspec_kw={"width_ratios": [1.3, 1.1, 1.4]})
    im = axes[0].imshow(matrix, cmap="YlOrRd", aspect="auto")
    axes[0].set_xticks(range(len(regions)))
    axes[0].set_xticklabels(regions)
    axes[0].set_yticks(range(len(samples)))
    axes[0].set_yticklabels([labels.get(s, s).split(" (")[0] for s in samples], fontsize=8)
    axes[0].set_title("Nucleotide variants by region")
    for i in range(len(samples)):
        for j in range(len(regions)):
            axes[0].text(j, i, str(matrix[i, j]), ha="center", va="center", fontsize=8,
                         color="white" if matrix[i, j] > matrix.max() * 0.6 else "#333333")
    plt.colorbar(im, ax=axes[0], fraction=0.046, pad=0.04, label="count")

    bottom = np.zeros(len(samples))
    colors = {"synonymous": "#9ecae1", "nonsynonymous": "#e6550d", "stop_gained": "#a50f15", "uncertain": "#bdbdbd"}
    for effect in effect_types:
        values = np.array([effect_counts[sample].get(effect, 0) for sample in samples])
        axes[1].bar(range(len(samples)), values, bottom=bottom, color=colors[effect], label=effect)
        bottom += values
    axes[1].set_xticks(range(len(samples)))
    axes[1].set_xticklabels([labels.get(s, s).split(" (")[0] for s in samples], rotation=30, ha="right", fontsize=8)
    axes[1].set_ylabel("Amino-acid changes")
    axes[1].set_title("Effect class per sample")
    axes[1].legend(frameon=False, fontsize=7)
    axes[1].spines[["top", "right"]].set_visible(False)

    variants = read_tsv(results / "variants" / "nucleotide_variants.tsv")
    bins = np.arange(0, 3251, 250)
    for sample in samples:
        positions = [int(row["position"]) for row in variants if row["sample"] == sample]
        counts, _ = np.histogram(positions, bins=bins)
        axes[2].plot((bins[:-1] + bins[1:]) / 2, counts, marker="o", markersize=3,
                     label=labels.get(sample, sample).split(" (")[0], linewidth=1.4)
    axes[2].set_xlabel("Genome position (bp)")
    axes[2].set_ylabel("Variants per 250 bp")
    axes[2].set_title("Variant density along the genome")
    axes[2].legend(frameon=False, fontsize=7)
    axes[2].spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(outdir / "mutation_summary.png", dpi=300)
    plt.close(fig)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", default="results")
    parser.add_argument("--metadata", default="comparative/all_hbv_metadata.tsv")
    parser.add_argument("--tree", default="results/phylogeny/hbv_phylogeny.rooted.treefile")
    parser.add_argument("--outdir", default="results/figures")
    args = parser.parse_args()

    results = Path(args.results)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    labels = sample_labels(Path(args.metadata))

    plot_coverage(results, outdir, labels)
    plot_qc(results, outdir, labels)
    plot_tree(Path(args.tree), Path(args.metadata), outdir, labels)
    plot_genome_structure(outdir)
    plot_mutations(results, outdir, labels)
    print(f"figures written to {outdir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
