#!/usr/bin/env python3
"""Extract HBV coding-region slices from the whole-genome alignment."""

from __future__ import annotations

import argparse
from pathlib import Path

from Bio import AlignIO

REGIONS = {
    "S": [(157, 837)],
    "P": [(2309, 3182), (1, 1625)],
    "X": [(1376, 1840)],
    "C": [(1816, 2454)],
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--alignment", default="alignment/hbv_alignment.fasta")
    parser.add_argument("--reference-id", default="NC_003977.2")
    parser.add_argument("--outdir", default="alignment/regions")
    args = parser.parse_args()

    alignment = AlignIO.read(args.alignment, "fasta")
    reference = None
    for record in alignment:
        if record.id.split("|")[0] == args.reference_id:
            reference = str(record.seq).upper()
            break
    if reference is None:
        raise SystemExit(f"reference {args.reference_id} not found in alignment")

    refpos_to_column = {}
    refpos = 0
    for column, base in enumerate(reference):
        if base != "-":
            refpos += 1
            refpos_to_column[refpos] = column

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    for name, segments in REGIONS.items():
        columns = []
        for start, end in segments:
            columns.extend(
                refpos_to_column[position]
                for position in range(start, end + 1)
                if position in refpos_to_column
            )
        if not columns:
            continue
        path = outdir / f"hbv_{name}.fasta"
        with path.open("w") as handle:
            for record in alignment:
                sequence = "".join(str(record.seq)[column] for column in columns)
                handle.write(f">{record.id}\n")
                for i in range(0, len(sequence), 70):
                    handle.write(sequence[i : i + 70] + "\n")
        print(f"{name}: {len(columns)} alignment columns -> {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
