#!/usr/bin/env python3
"""Convert an nf-core/fetchngs samplesheet.csv into an nf-core/bacass samplesheet.tsv.

bacass expects a TSV with columns: ID, R1, R2, LongFastQ, Fast5, GenomeSize
fetchngs emits a CSV with at least: sample, fastq_1, fastq_2
"""
import argparse
import csv
import sys


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", required=True, help="fetchngs samplesheet.csv")
    ap.add_argument("--output", required=True, help="bacass samplesheet.tsv")
    args = ap.parse_args()

    with open(args.input, newline="") as fh:
        reader = csv.DictReader(fh)
        cols = {c.lower(): c for c in (reader.fieldnames or [])}
        sample = cols.get("sample")
        r1 = cols.get("fastq_1")
        r2 = cols.get("fastq_2")
        if not (sample and r1):
            sys.exit(f"Unexpected fetchngs columns: {reader.fieldnames}")

        n = 0
        with open(args.output, "w", newline="") as out:
            writer = csv.writer(out, delimiter="\t")
            writer.writerow(["ID", "R1", "R2", "LongFastQ", "Fast5", "GenomeSize"])
            for row in reader:
                writer.writerow(
                    [row[sample], row[r1], (row.get(r2) if r2 else None) or "NA", "NA", "NA", "NA"]
                )
                n += 1

    print(f"Wrote {n} samples to {args.output}", file=sys.stderr)


if __name__ == "__main__":
    main()
