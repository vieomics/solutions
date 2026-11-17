#!/usr/bin/env python3
"""Summarise a multiple sequence alignment without removing variable sites."""

from __future__ import annotations

import argparse
import csv
from collections import Counter
from pathlib import Path

from Bio import AlignIO


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default="alignment/hbv_alignment.fasta")
    parser.add_argument("--outdir", default="alignment")
    args = parser.parse_args()

    alignment = AlignIO.read(args.alignment, "fasta")
    nseq = len(alignment)
    length = alignment.get_alignment_length()
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    gap_total = 0
    n_total = 0
    variable = 0
    informative = 0
    singleton = 0
    constant = 0
    gap_rich = []
    variable_rows = []

    for i in range(length):
        column = alignment[:, i].upper()
        counts = Counter(column)
        gap_total += counts.get("-", 0)
        n_total += counts.get("N", 0)
        informative_counts = [
            count for base, count in counts.items() if base not in "-N" and count >= 2
        ]
        bases = {base for base in counts if base not in "-N"}
        if len(bases) <= 1:
            constant += 1
        else:
            variable += 1
            if len(informative_counts) >= 2:
                informative += 1
            elif sum(1 for count in counts.values() if count == 1 and count) >= 1:
                singleton += 1
            variable_rows.append(
                {
                    "alignment_position": i + 1,
                    "gaps": counts.get("-", 0),
                    "n_bases": counts.get("N", 0),
                    "a": counts.get("A", 0),
                    "c": counts.get("C", 0),
                    "g": counts.get("G", 0),
                    "t": counts.get("T", 0),
                    "parsimony_informative": "yes" if len(informative_counts) >= 2 else "no",
                }
            )
        gap_fraction = counts.get("-", 0) / nseq
        if gap_fraction > 0.5:
            gap_rich.append(i + 1)

    per_sequence = []
    for record in alignment:
        seq = str(record.seq).upper()
        ungapped = len(seq.replace("-", ""))
        per_sequence.append(
            {
                "id": record.id,
                "alignment_length": len(seq),
                "ungapped_length": ungapped,
                "gaps": seq.count("-"),
                "n_bases": seq.count("N"),
                "gap_fraction": f"{seq.count('-') / len(seq):.6f}",
                "n_fraction": f"{seq.count('N') / len(seq):.6f}",
            }
        )

    summary = [
        "HBV multiple sequence alignment summary",
        f"alignment_file: {args.alignment}",
        f"sequences: {nseq}",
        f"alignment_length: {length}",
        f"gap_fraction: {gap_total / (nseq * length):.6f}",
        f"n_fraction: {n_total / (nseq * length):.6f}",
        f"constant_sites: {constant}",
        f"variable_sites: {variable}",
        f"parsimony_informative_sites: {informative}",
        f"singleton_sites: {singleton}",
        f"gap_rich_positions_gt50pct: {len(gap_rich)}",
        "gap_rich_ranges: " + (", ".join(map(str, gap_rich[:50])) if gap_rich else "none"),
        "note: no columns were removed; variable and gap-rich regions are reported rather than trimmed",
    ]
    (outdir / "alignment_stats.txt").write_text("\n".join(summary) + "\n")

    with (outdir / "alignment_stats.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["metric", "value"])
        writer.writerow(["sequences", nseq])
        writer.writerow(["alignment_length", length])
        writer.writerow(["gap_fraction", f"{gap_total / (nseq * length):.6f}"])
        writer.writerow(["n_fraction", f"{n_total / (nseq * length):.6f}"])
        writer.writerow(["constant_sites", constant])
        writer.writerow(["variable_sites", variable])
        writer.writerow(["parsimony_informative_sites", informative])
        writer.writerow(["singleton_sites", singleton])
        writer.writerow(["gap_rich_positions_gt50pct", len(gap_rich)])

    with (outdir / "per_sequence_stats.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(per_sequence[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(per_sequence)

    with (outdir / "variable_sites.tsv").open("w", newline="") as handle:
        fields = ["alignment_position", "gaps", "n_bases", "a", "c", "g", "t", "parsimony_informative"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(variable_rows)

    print("\n".join(summary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
