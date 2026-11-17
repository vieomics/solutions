#!/usr/bin/env python3
"""Create the nf-core/viralrecon samplesheet from metadata/selected_samples.tsv."""

import argparse
import csv
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--metadata", default="metadata/selected_samples.tsv")
    parser.add_argument("--fastq-dir", default="data/fastq")
    parser.add_argument("--out", default="samplesheet.csv")
    args = parser.parse_args()

    root = Path.cwd()
    rows = []
    with open(args.metadata, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            sample = row["sample"]
            rows.append(
                {
                    "sample": sample,
                    "fastq_1": str((root / args.fastq_dir / f"{sample}_R1.fastq.gz").resolve()),
                    "fastq_2": str((root / args.fastq_dir / f"{sample}_R2.fastq.gz").resolve()),
                }
            )

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "fastq_1", "fastq_2"])
        writer.writeheader()
        writer.writerows(rows)
    print(f"wrote {out} ({len(rows)} samples)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
