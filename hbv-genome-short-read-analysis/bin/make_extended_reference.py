#!/usr/bin/env python3
"""Create an origin-extended HBV reference for circular-aware short-read mapping.

The genome is linearised at the NC_003977.2 origin.  Reads spanning that
arbitrary origin cannot map to a plain linear reference.  Duplicating the first
``--extension-length`` bases at the end lets those reads align across the
junction; the duplicated tail is projected back to coordinates 1..L when depth
and allele counts are calculated.
"""

import argparse
from pathlib import Path

from Bio import SeqIO


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", default="references/hbv_reference.fasta")
    parser.add_argument("--out", default="references/hbv_reference.extended.fasta")
    parser.add_argument("--extension-length", type=int, default=500)
    parser.add_argument("--name", default=None)
    args = parser.parse_args()

    record = next(SeqIO.parse(args.reference, "fasta"))
    seq = str(record.seq).upper()
    ext = args.extension_length
    if ext < 1 or ext >= len(seq):
        raise SystemExit("extension length must be between 1 and genome length - 1")

    name = args.name or f"{record.id}_ext{ext}"
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    extended = seq + seq[:ext]
    with out.open("w") as handle:
        handle.write(f">{name} origin-extended HBV reference; first {ext} bp duplicated at the 3' end\n")
        for i in range(0, len(extended), 70):
            handle.write(extended[i : i + 70] + "\n")
    print(f"wrote {out}: {len(seq)} bp + {ext} bp duplicate = {len(extended)} bp")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
