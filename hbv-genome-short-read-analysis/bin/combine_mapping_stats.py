#!/usr/bin/env python3
"""Combine per-sample mapping, circular coverage and consensus QC tables."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


def read_metrics(path: Path) -> dict[str, str]:
    values = {}
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            values[row["metric"]] = row["value"]
    return values


def parse_flagstat(path: Path) -> dict[str, str]:
    text = path.read_text() if path.exists() else ""
    total = re.search(r"^(\d+) \+ \d+ in total", text, re.M)
    mapped = re.search(r"^(\d+) \+ \d+ mapped \(([^)]+)\)", text, re.M)
    properly = re.search(r"^(\d+) \+ \d+ properly paired \(([^)]+)\)", text, re.M)
    return {
        "total_reads": total.group(1) if total else "",
        "mapped_reads": mapped.group(1) if mapped else "",
        "mapping_rate": mapped.group(2).split()[0] if mapped else "",
        "properly_paired": properly.group(1) if properly else "",
        "properly_paired_pct": properly.group(2).split()[0] if properly else "",
    }


def parse_bowtie2(path: Path) -> str:
    if not path.exists():
        return ""
    match = re.search(r"([0-9.]+)% overall alignment rate", path.read_text())
    return match.group(1) + "%" if match else ""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mapping-dir", default="results/mapping")
    parser.add_argument("--consensus-dir", default="results/consensus")
    parser.add_argument("--viralrecon-dir", default="results/viralrecon")
    parser.add_argument("--samples", default="metadata/selected_samples.tsv")
    args = parser.parse_args()

    mapping_dir = Path(args.mapping_dir)
    consensus_dir = Path(args.consensus_dir)
    samples = []
    with open(args.samples, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            samples.append(row)

    rows = []
    depth_rows = []
    coverage_rows = []
    consensus_rows = []
    for sample in samples:
        name = sample["sample"]
        coverage = read_metrics(consensus_dir / f"{name}.coverage.tsv")
        flagstat = parse_flagstat(mapping_dir / f"{name}.flagstat.txt")
        bowtie2 = parse_bowtie2(
            Path(args.viralrecon_dir)
            / "variants"
            / "bowtie2"
            / "log"
            / f"{name}.bowtie2.log"
        )
        row = {
            "sample": name,
            "run_accession": sample["run_accession"],
            "alias": sample["alias"],
            "genotype": sample["genotype"],
            "country": sample["country"],
            "collection_date": sample["collection_date"],
            "bwa_total_reads": flagstat["total_reads"],
            "bwa_mapped_reads": flagstat["mapped_reads"],
            "bwa_mapping_rate": flagstat["mapping_rate"],
            "bwa_properly_paired_pct": flagstat["properly_paired_pct"],
            "bowtie2_overall_alignment_rate": bowtie2,
            "mean_depth": coverage.get("mean_depth", ""),
            "median_depth": coverage.get("median_depth", ""),
            "breadth_1x_pct": coverage.get("breadth_1x_pct", ""),
            "breadth_10x_pct": coverage.get("breadth_10x_pct", ""),
            "breadth_100x_pct": coverage.get("breadth_100x_pct", ""),
            "origin_spanning_reads": coverage.get("origin_spanning_reads", ""),
            "consensus_length": coverage.get("final_length", ""),
            "consensus_n_bases": coverage.get("final_n_bases", ""),
            "consensus_source": coverage.get("consensus_source", ""),
        }
        rows.append(row)
        for key, value in coverage.items():
            coverage_rows.append({"sample": name, "metric": key, "value": value})
        consensus_rows.append(
            {
                "sample": name,
                "genotype": sample["genotype"],
                "consensus_length": row["consensus_length"],
                "n_bases": row["consensus_n_bases"],
                "n_fraction": f"{int(row['consensus_n_bases']) / int(row['consensus_length']):.6f}"
                if row["consensus_length"] and row["consensus_n_bases"]
                else "",
                "mean_depth": row["mean_depth"],
                "breadth_10x_pct": row["breadth_10x_pct"],
                "origin_spanning_reads": row["origin_spanning_reads"],
                "consensus_source": row["consensus_source"],
                "interpretation": (
                    "partial genome: low-coverage block masked as N"
                    if row["consensus_n_bases"] and int(row["consensus_n_bases"]) / int(row["consensus_length"]) > 0.05
                    else "genome-wide coverage adequate"
                ),
            }
        )
        depth_path = consensus_dir / f"{name}.depth.tsv"
        if depth_path.exists():
            with depth_path.open(newline="") as handle:
                for depth in csv.DictReader(handle, delimiter="\t"):
                    depth_rows.append(
                        {
                            "sample": name,
                            "position": depth["position"],
                            "depth": depth["depth"],
                            "major_allele": depth["major_allele"],
                            "major_fraction": depth["major_fraction"],
                            "consensus_call": depth["consensus_call"],
                        }
                    )

    mapping_fields = list(rows[0].keys())
    with (mapping_dir / "mapping_stats.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=mapping_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    with (mapping_dir / "mapping_stats.txt").open("w") as handle:
        handle.write("Per-sample mapping and circular coverage summary\n")
        handle.write("sample\tBWA mapping rate\tmean depth\tbreadth>=10x\torigin-spanning reads\tconsensus length\tN bases\n")
        for row in rows:
            handle.write(
                f"{row['sample']}\t{row['bwa_mapping_rate']}\t{row['mean_depth']}x\t"
                f"{row['breadth_10x_pct']}%\t{row['origin_spanning_reads']}\t"
                f"{row['consensus_length']} bp\t{row['consensus_n_bases']}\n"
            )

    with (mapping_dir / "depth.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["sample", "position", "depth", "major_allele", "major_fraction", "consensus_call"],
            delimiter="\t",
        )
        writer.writeheader()
        writer.writerows(depth_rows)
    with (mapping_dir / "coverage.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "metric", "value"], delimiter="\t")
        writer.writeheader()
        writer.writerows(coverage_rows)
    with (consensus_dir / "consensus_stats.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(consensus_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(consensus_rows)

    print(f"wrote mapping and consensus summaries for {len(rows)} samples")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
