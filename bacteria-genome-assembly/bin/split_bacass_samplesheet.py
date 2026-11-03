#!/usr/bin/env python3
"""Split an nf-core/bacass samplesheet into one TSV per sample.

bacass expects a TSV with columns: ID, R1, R2, LongFastQ, Fast5, GenomeSize.

By default the output filename is taken from the ``ID`` column. If the combined
sheet uses ENA experiment accessions (``ERX...``) but the jobs should be named
after the run accession (``ERR...``), extract the name from ``R1`` instead:

    python3 bin/split_bacass_samplesheet.py \
        --input bacass_samplesheet.tsv \
        --outdir samplesheets/local \
        --sample-regex '(ERR[0-9]+)'

The script is deliberately dependency-free so it can run before ``pixi install``.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from pathlib import Path

REQUIRED = ["ID", "R1", "R2", "LongFastQ", "Fast5", "GenomeSize"]


def sample_name(row: dict[str, str], args: argparse.Namespace) -> str:
    if args.sample_regex:
        value = row.get(args.regex_field, "")
        match = re.search(args.sample_regex, value)
        if not match:
            sys.exit(
                f"Cannot extract a sample name from {args.regex_field}={value!r} "
                f"using {args.sample_regex!r}"
            )
        return match.group(1)
    return row[args.name_column]


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="combined bacass samplesheet.tsv")
    parser.add_argument("--outdir", default="samplesheets", help="output directory")
    parser.add_argument("--name-column", default="ID", help="column to use as the sample name")
    parser.add_argument(
        "--sample-regex",
        help="regex with one capture group used to derive the sample name",
    )
    parser.add_argument(
        "--regex-field",
        default="R1",
        choices=["ID", "R1", "R2"],
        help="column the --sample-regex is applied to",
    )
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    with open(args.input, newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        fields = reader.fieldnames or []
        missing = [field for field in REQUIRED if field not in fields]
        if missing:
            sys.exit(f"Missing column(s) in {args.input}: {', '.join(missing)}")
        rows = list(reader)

    if not rows:
        sys.exit(f"No data rows in {args.input}")

    for row in rows:
        name = sample_name(row, args)
        target = outdir / f"{name}.tsv"
        with open(target, "w", newline="") as handle:
            writer = csv.DictWriter(
                handle,
                fieldnames=fields,
                delimiter="\t",
                extrasaction="ignore",
            )
            writer.writeheader()
            writer.writerow(row)

    print(f"Wrote {len(rows)} samples to {outdir}", file=sys.stderr)


if __name__ == "__main__":
    main()
