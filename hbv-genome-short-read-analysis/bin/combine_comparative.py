#!/usr/bin/env python3
"""Combine the five study consensus genomes with the curated public panel."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from Bio import SeqIO


def read_fasta(path: Path) -> dict[str, str]:
    return {record.id: str(record.seq).upper() for record in SeqIO.parse(path, "fasta")}


def label_for(row: dict) -> str:
    country = row["country"].replace(" ", "_")
    date = row["collection_date"].replace(" ", "_")
    return f"{row['id']}|{row['genotype']}|{country}|{date}"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--public-fasta", default="references/hbv_public_genomes.fasta")
    parser.add_argument("--public-metadata", default="references/hbv_metadata.tsv")
    parser.add_argument("--consensus-dir", default="results/consensus")
    parser.add_argument("--coverage-dir", default=None)
    parser.add_argument("--sample-metadata", default="metadata/selected_samples.tsv")
    parser.add_argument("--outdir", default="comparative")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    public = {
        record.id.split("|")[0]: str(record.seq).upper()
        for record in SeqIO.parse(args.public_fasta, "fasta")
    }
    samples = {}
    for path in sorted(Path(args.consensus_dir).glob("*.consensus.fasta")):
        if path.name.endswith(".circular.consensus.fasta"):
            continue
        for record in SeqIO.parse(path, "fasta"):
            if record.id.endswith("_circular"):
                continue
            samples[record.id] = str(record.seq).upper()

    sample_meta = {}
    with open(args.sample_metadata, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            sample_meta[row["sample"]] = row

    coverage = {}
    for sample in samples:
        coverage_path = Path(args.coverage_dir or args.consensus_dir) / f"{sample}.coverage.tsv"
        values = {}
        if coverage_path.exists():
            with coverage_path.open(newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    values[row["metric"]] = row["value"]
        coverage[sample] = values

    public_meta = {}
    with open(args.public_metadata, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            public_meta[row["accession"]] = row

    rows = []
    sequences = []
    for accession, row in public_meta.items():
        if accession not in public:
            continue
        seq = public[accession]
        rows.append(
            {
                "id": accession,
                "accession": accession,
                "sample": "",
                "genotype": row["genotype"],
                "subgenotype": row["subgenotype"],
                "country": row["country"],
                "collection_date": row["collection_date"],
                "sequence_length": len(seq),
                "n_bases": seq.count("N"),
                "n_fraction": f"{seq.count('N') / len(seq):.6f}",
                "source": "GenBank",
                "record_type": "public_reference",
                "isolate": row.get("isolate", ""),
                "notes": row.get("role", ""),
                "breadth_10x_pct": "",
                "mean_depth": "",
                "coverage_note": "",
            }
        )
        sequences.append((label_for(rows[-1]), seq))

    for sample, seq in sorted(samples.items()):
        meta = sample_meta.get(sample, {})
        rows.append(
            {
                "id": sample,
                "accession": meta.get("run_accession", ""),
                "sample": sample,
                "genotype": meta.get("genotype", ""),
                "subgenotype": meta.get("genotype", ""),
                "country": meta.get("country", "Brazil"),
                "collection_date": meta.get("collection_date", ""),
                "sequence_length": len(seq),
                "n_bases": seq.count("N"),
                "n_fraction": f"{seq.count('N') / len(seq):.6f}",
                "source": "this study (PRJNA659786)",
                "record_type": "study_consensus",
                "isolate": meta.get("alias", "").replace("/", "_"),
                "notes": "nf-core/viralrecon consensus patched with circular-origin evidence",
                "breadth_10x_pct": coverage[sample].get("breadth_10x_pct", ""),
                "mean_depth": coverage[sample].get("mean_depth", ""),
                "coverage_note": (
                    "partial genome; low-coverage block masked as N"
                    if seq.count("N") / len(seq) > 0.05
                    else "genome-wide coverage adequate"
                ),
            }
        )
        sequences.append((label_for(rows[-1]), seq))

    ids = [row["id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise SystemExit("duplicate sequence identifiers in comparative set")
    for row in rows:
        if not (3000 <= row["sequence_length"] <= 3300):
            raise SystemExit(f"{row['id']}: unexpected length {row['sequence_length']}")
        if row["record_type"] == "public_reference" and row["n_bases"] / row["sequence_length"] > 0.05:
            raise SystemExit(f"{row['id']}: >5% ambiguous bases in public reference")
        if row["record_type"] == "study_consensus" and row["n_bases"] / row["sequence_length"] > 0.60:
            raise SystemExit(f"{row['id']}: >60% ambiguous bases; consensus is not analysable")

    fasta_path = outdir / "all_hbv_sequences.fasta"
    with fasta_path.open("w") as handle:
        for label, seq in sequences:
            handle.write(f">{label}\n")
            for i in range(0, len(seq), 70):
                handle.write(seq[i : i + 70] + "\n")

    fields = [
        "id", "accession", "sample", "genotype", "subgenotype", "country",
        "collection_date", "sequence_length", "n_bases", "n_fraction",
        "source", "record_type", "isolate", "notes",
        "breadth_10x_pct", "mean_depth", "coverage_note",
    ]
    with (outdir / "all_hbv_metadata.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    genotype_counts = {}
    for row in rows:
        genotype_counts[row["genotype"]] = genotype_counts.get(row["genotype"], 0) + 1
    checks = [
        "Comparative HBV sequence set",
        f"sequences: {len(rows)} ({len(public_meta)} public + {len(samples)} study consensus)",
        f"identifiers unique: yes",
        f"length range: {min(r['sequence_length'] for r in rows)}-{max(r['sequence_length'] for r in rows)} bp",
        f"maximum N fraction: {max(r['n_bases'] / r['sequence_length'] for r in rows):.4%}",
        "genotype counts: " + ", ".join(f"{k}={v}" for k, v in sorted(genotype_counts.items())),
        "all sequences are represented 5'->3' in the NC_003977.2 coordinate frame",
        "public sequences were origin-normalised by a unique 25-mer vote (see references/hbv_metadata.tsv)",
        "study consensus sequences were generated against NC_003977.2 and boundary-patched with circular mapping",
    ]
    for sample in sorted(samples):
        seq = samples[sample]
        checks.append(
            f"{sample}: {len(seq)} bp, N={seq.count('N')} ({seq.count('N')/len(seq):.1%}), "
            f"breadth>=10x={coverage[sample].get('breadth_10x_pct','NA')}%, "
            f"mean depth={coverage[sample].get('mean_depth','NA')}x"
        )
    (outdir / "comparative_checks.txt").write_text("\n".join(checks) + "\n")
    print("\n".join(checks))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
