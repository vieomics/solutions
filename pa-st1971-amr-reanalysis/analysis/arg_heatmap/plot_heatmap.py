#!/usr/bin/env python3
"""Build the Fig. 1B-style ARG heatmap for the 13 available ST1971 genomes.

Inputs
------
results/heatmap/genomes.tsv
results/heatmap/amrfinder/<accession>.tsv

Outputs
-------
results/heatmap/arg_matrix.tsv
results/heatmap/arg_hits_long.tsv
results/heatmap/summary.tsv
results/heatmap/arg_heatmap.png

The paper's Fig. 1B contains 25 genomes: strain 71, 12 other assemblies and 12
raw-read-only genomes. The 12 raw-read entries are not assembled here, so this
figure uses the 13 genomes that are public as GCA assemblies (including strain
71). Rows are clustered by ARG copy-number profile; columns are grouped by
antibiotic class and then gene name.
"""
from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.colors import BoundaryNorm, ListedColormap
from matplotlib.patches import Patch
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import pdist

ROOT = Path(__file__).resolve().parent.parent.parent
HEATMAP_DIR = ROOT / "results" / "heatmap"
AMRDIR = HEATMAP_DIR / "amrfinder"
GENOMES_TSV = HEATMAP_DIR / "genomes.tsv"
OUT_PNG = HEATMAP_DIR / "arg_heatmap.png"

# Paper-like class order: common acquired classes first.
CLASS_ORDER = [
    "AMINOGLYCOSIDE",
    "BETA-LACTAM",
    "FOSFOMYCIN",
    "PHENICOL",
    "QUINOLONE",
    "SULFONAMIDE",
    "TETRACYCLINE",
    "TRIMETHOPRIM",
    "MACROLIDE",
    "MULTIDRUG",
]
CLASS_COLORS = {
    "AMINOGLYCOSIDE": "#2166ac",
    "BETA-LACTAM": "#1b7837",
    "FOSFOMYCIN": "#f39c12",
    "PHENICOL": "#8e44ad",
    "QUINOLONE": "#8c564b",
    "SULFONAMIDE": "#17becf",
    "TETRACYCLINE": "#bcbd22",
    "TRIMETHOPRIM": "#e377c2",
    "MACROLIDE": "#aec7e8",
    "MULTIDRUG": "#7f7f7f",
}
HIT_COLORS = ["#e6e6e6", "#fdae61", "#f46d43", "#d73027"]
MAX_COPIES = 3


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def read_genomes() -> list[dict[str, str]]:
    rows = read_tsv(GENOMES_TSV)
    if not rows:
        raise SystemExit(f"No genomes in {GENOMES_TSV}")
    return rows


def read_amr_hits(path: Path) -> list[tuple[str, str]]:
    """Return (gene, class) for acquired AMR rows, excluding point calls."""
    hits: list[tuple[str, str]] = []
    for row in read_tsv(path):
        if row.get("Type", row.get("Element type", "")) != "AMR":
            continue
        if row.get("Method", "").startswith("POINT"):
            continue
        gene = row.get("Element symbol", row.get("Gene symbol", "")).strip()
        if not gene:
            continue
        drug_class = row.get("Class", "unclassified").strip() or "unclassified"
        hits.append((gene, drug_class))
    return hits


def class_color(drug_class: str) -> str:
    if drug_class in CLASS_COLORS:
        return CLASS_COLORS[drug_class]
    cmap = plt.get_cmap("tab20")
    index = sum(ord(char) for char in drug_class) % 20
    return mcolors.to_hex(cmap(index))


def main() -> None:
    genomes = read_genomes()
    count_by_genome: dict[str, Counter[str]] = {}
    class_by_gene: dict[str, set[str]] = defaultdict(set)

    for genome in genomes:
        accession = genome["accession"]
        path = AMRDIR / f"{accession}.tsv"
        if not path.is_file():
            raise SystemExit(f"Missing {path}; run analysis/arg_heatmap/run_amrfinder.sh")
        hits = read_amr_hits(path)
        count_by_genome[accession] = Counter(gene for gene, _ in hits)
        for gene, drug_class in hits:
            class_by_gene[gene].add(drug_class)

    genes = sorted(
        class_by_gene,
        key=lambda gene: (
            CLASS_ORDER.index(next(iter(sorted(class_by_gene[gene]))))
            if next(iter(sorted(class_by_gene[gene]))) in CLASS_ORDER
            else len(CLASS_ORDER),
            next(iter(sorted(class_by_gene[gene]))),
            gene.lower(),
        ),
    )
    if not genes:
        raise SystemExit("No acquired ARG hits found in the 13 genomes")

    gene_class = {
        gene: next(iter(sorted(class_by_gene[gene]))) for gene in genes
    }
    matrix = np.zeros((len(genomes), len(genes)), dtype=int)
    for row_index, genome in enumerate(genomes):
        counts = count_by_genome[genome["accession"]]
        for col_index, gene in enumerate(genes):
            matrix[row_index, col_index] = min(counts.get(gene, 0), MAX_COPIES)

    # Cluster genomes by ARG copy-number profile. With 13 nearly clonal
    # genomes this is mostly a presentation aid, not a population structure.
    row_order = list(range(len(genomes)))
    if len(genomes) > 2:
        distances = pdist(matrix, metric="euclidean")
        if np.any(distances > 0):
            tree = linkage(distances, method="average", optimal_ordering=True)
            row_order = dendrogram(tree, no_plot=True)["leaves"]
    else:
        tree = None
    matrix = matrix[row_order]
    genomes = [genomes[index] for index in row_order]

    # ------------------------------------------------------------------
    # Write machine-readable matrices first.
    # ------------------------------------------------------------------
    with (HEATMAP_DIR / "arg_matrix.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["accession", "label", "country", *genes])
        for genome, values in zip(genomes, matrix):
            writer.writerow(
                [
                    genome["accession"],
                    genome["label"],
                    genome["country"],
                    *[str(value) for value in values],
                ]
            )

    with (HEATMAP_DIR / "arg_hits_long.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["accession", "label", "country", "gene", "class", "copies"])
        for genome, values in zip(genomes, matrix):
            for gene, value in zip(genes, values):
                if value:
                    writer.writerow(
                        [
                            genome["accession"],
                            genome["label"],
                            genome["country"],
                            gene,
                            gene_class[gene],
                            value,
                        ]
                    )

    study_row = next(
        (
            index
            for index, genome in enumerate(genomes)
            if genome["country"] == "Vietnam"
        ),
        None,
    )
    per_genome = [int(row.sum()) for row in matrix]
    with (HEATMAP_DIR / "summary.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["genomes", len(genomes)])
        writer.writerow(["genes", len(genes)])
        writer.writerow(["max_copies_capped_at", MAX_COPIES])
        writer.writerow(["ARG copies per genome (min)", min(per_genome)])
        writer.writerow(["ARG copies per genome (max)", max(per_genome)])
        if study_row is not None:
            writer.writerow(["study_sample", genomes[study_row]["accession"]])
            writer.writerow(
                ["study_sample_ARG_copies", int(matrix[study_row].sum())]
            )

    # ------------------------------------------------------------------
    # Plot: dendrogram | heatmap | row metadata, with a class strip below.
    # ------------------------------------------------------------------
    n_rows, n_cols = matrix.shape
    fig = plt.figure(
        figsize=(max(14, 0.24 * n_cols + 6), max(6.2, 0.34 * n_rows + 4.5))
    )
    grid = fig.add_gridspec(
        2,
        3,
        width_ratios=[0.9, 8.5, 2.9],
        height_ratios=[22, 0.7],
        wspace=0.02,
        hspace=0.02,
    )
    ax_tree = fig.add_subplot(grid[0, 0])
    ax_heat = fig.add_subplot(grid[0, 1])
    ax_meta = fig.add_subplot(grid[0, 2], sharey=ax_heat)
    ax_strip = fig.add_subplot(grid[1, 1])

    hit_cmap = ListedColormap(HIT_COLORS)
    hit_norm = BoundaryNorm([-0.5, 0.5, 1.5, 2.5, 3.5], hit_cmap.N)
    image = ax_heat.imshow(
        matrix, aspect="auto", interpolation="nearest", cmap=hit_cmap, norm=hit_norm
    )
    ax_heat.set_xticks([])
    ax_heat.set_yticks([])
    fig.suptitle(
        "ARG profile of the 13 publicly available P. aeruginosa ST1971 genomes",
        x=0.01,
        ha="left",
        fontsize=12,
        y=0.97,
    )
    for spine in ax_heat.spines.values():
        spine.set_visible(False)

    if tree is not None:
        dendrogram(
            tree,
            orientation="left",
            no_labels=True,
            ax=ax_tree,
            color_threshold=0,
            above_threshold_color="#555555",
        )
        # Dendrogram leaves sit at 5, 15, ...; inverting puts the first leaf
        # at the top to match the heatmap row order.
        ax_tree.invert_yaxis()
        ax_tree.axis("off")
    else:
        ax_tree.axis("off")

    ax_meta.set_xlim(0, 1)
    ax_meta.set_ylim(n_rows - 0.5, -0.5)
    ax_meta.axis("off")
    for index, genome in enumerate(genomes):
        is_study = genome["country"] == "Vietnam"
        label = genome["label"]
        ax_meta.text(
            0.02,
            index,
            label,
            va="center",
            ha="left",
            fontsize=7.8 if not is_study else 8.4,
            fontweight="bold" if is_study else "normal",
            color="#b2182b" if is_study else "#222222",
        )
        ax_meta.text(
            0.02,
            index + 0.30,
            genome["country"],
            va="center",
            ha="left",
            fontsize=6.6,
            color="#666666",
        )

    class_names = sorted(
        {gene_class[gene] for gene in genes},
        key=lambda name: (
            CLASS_ORDER.index(name) if name in CLASS_ORDER else len(CLASS_ORDER),
            name,
        ),
    )
    class_to_index = {name: index for index, name in enumerate(class_names)}
    class_strip = np.array([[class_to_index[gene_class[gene]] for gene in genes]])
    ax_strip.imshow(
        class_strip,
        aspect="auto",
        interpolation="nearest",
        cmap=ListedColormap([class_color(name) for name in class_names]),
        norm=BoundaryNorm(np.arange(-0.5, len(class_names) + 0.5), len(class_names)),
    )
    ax_strip.set_xlim(-0.5, n_cols - 0.5)
    ax_strip.set_yticks([])
    ax_strip.set_xticks(range(n_cols), genes, rotation=90, fontsize=6.2)
    ax_strip.tick_params(axis="x", length=0, pad=2)
    for spine in ax_strip.spines.values():
        spine.set_visible(False)

    hit_handles = [
        Patch(facecolor=color, edgecolor="#999999", label=str(value))
        for value, color in enumerate(HIT_COLORS)
    ]
    fig.legend(
        handles=hit_handles,
        title="ARG copies",
        loc="lower right",
        bbox_to_anchor=(0.99, 0.0),
        ncol=4,
        frameon=False,
        fontsize=8,
        title_fontsize=8,
    )
    class_handles = [
        Patch(facecolor=class_color(name), label=name) for name in class_names
    ]
    fig.legend(
        handles=class_handles,
        title="Antibiotic class",
        loc="lower left",
        bbox_to_anchor=(0.01, 0.0),
        ncol=min(4, len(class_handles)),
        frameon=False,
        fontsize=7.5,
        title_fontsize=8,
    )

    fig.subplots_adjust(left=0.02, right=0.98, top=0.91, bottom=0.22)
    HEATMAP_DIR.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PNG, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"[heatmap] {n_rows} genomes x {n_cols} ARG columns")
    print(f"[heatmap] {int(matrix.sum())} ARG copies in the matrix")
    print(f"[heatmap] wrote {OUT_PNG}")
    print(f"[heatmap] wrote {HEATMAP_DIR / 'arg_matrix.tsv'}")
    print(f"[heatmap] wrote {HEATMAP_DIR / 'arg_hits_long.tsv'}")
    print(f"[heatmap] wrote {HEATMAP_DIR / 'summary.tsv'}")


if __name__ == "__main__":
    main()
