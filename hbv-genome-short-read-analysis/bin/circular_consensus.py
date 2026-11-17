#!/usr/bin/env python3
"""Circular-aware HBV depth, allele counts, consensus and boundary patching.

Reads are mapped to an origin-extended reference (genome + first N bases
duplicated).  Every alignment position is projected modulo the genome length,
so depth and allele counts represent the circular genome rather than a linear
copy.  The script then:

* writes per-base depth/allele counts and coverage summaries;
* builds a majority-rule circular consensus (N below the depth threshold);
* patches Ns at the ends of the nf-core/viralrecon consensus with the circular
  evidence, while keeping the indel-aware viralrecon sequence elsewhere;
* records positions that differ between the two consensus representations.
"""

from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter
from pathlib import Path

import pysam
from Bio import SeqIO


def load_fasta(path: str) -> tuple[str, str]:
    record = next(SeqIO.parse(path, "fasta"))
    return record.id, str(record.seq).upper()


def write_fasta(path: Path, name: str, seq: str) -> None:
    with path.open("w") as handle:
        handle.write(f">{name}\n")
        for i in range(0, len(seq), 70):
            handle.write(seq[i : i + 70] + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bam", required=True)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--sample", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--viralrecon-consensus", default=None)
    parser.add_argument("--min-depth", type=int, default=10)
    parser.add_argument("--min-allele-fraction", type=float, default=0.75)
    parser.add_argument("--min-base-quality", type=int, default=20)
    parser.add_argument("--min-mapping-quality", type=int, default=0)
    args = parser.parse_args()

    ref_name, ref_seq = load_fasta(args.reference)
    genome_length = len(ref_seq)
    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    counts = [Counter() for _ in range(genome_length)]
    stats = Counter()
    bam = pysam.AlignmentFile(args.bam, "rb")
    for read in bam.fetch(until_eof=True):
        if read.is_unmapped or read.is_secondary or read.is_supplementary or read.is_qcfail:
            continue
        if read.mapping_quality < args.min_mapping_quality:
            continue
        stats["reads_considered"] += 1
        qualities = read.query_qualities
        for query_pos, ref_pos in read.get_aligned_pairs(matches_only=False):
            if ref_pos is None:
                continue
            position = ref_pos + 1
            if position > genome_length:
                position -= genome_length
            if position < 1 or position > genome_length:
                continue
            slot = counts[position - 1]
            if query_pos is None:
                slot["del"] += 1
                continue
            if qualities is not None and qualities[query_pos] < args.min_base_quality:
                continue
            base = read.query_sequence[query_pos].upper()
            if base in "ACGTN":
                slot[base] += 1
        if (
            read.reference_start < genome_length
            and read.reference_end is not None
            and read.reference_end > genome_length
        ):
            stats["origin_spanning_reads"] += 1
    bam.close()

    depth_rows = []
    calls = []
    depths = []
    deletions = 0
    for index, ref_base in enumerate(ref_seq, start=1):
        slot = counts[index - 1]
        depth = sum(slot.values())
        depths.append(depth)
        ranked = sorted(
            ((base, slot.get(base, 0)) for base in ("A", "C", "G", "T", "del")),
            key=lambda item: (-item[1], item[0]),
        )
        major, major_count = ranked[0]
        fraction = major_count / depth if depth else 0.0
        if depth < args.min_depth:
            call = "N"
            reason = "low_depth"
        elif major == "del" and fraction >= args.min_allele_fraction:
            call = "-"
            reason = "deletion"
            deletions += 1
        elif major in "ACGT" and fraction >= args.min_allele_fraction:
            call = major
            reason = "majority"
        else:
            call = "N"
            reason = "ambiguous"
        calls.append(call)
        depth_rows.append(
            {
                "position": index,
                "ref_base": ref_base,
                "depth": depth,
                "A": slot.get("A", 0),
                "C": slot.get("C", 0),
                "G": slot.get("G", 0),
                "T": slot.get("T", 0),
                "N": slot.get("N", 0),
                "deletion": slot.get("del", 0),
                "major_allele": major,
                "major_fraction": f"{fraction:.6f}",
                "consensus_call": call,
                "reason": reason,
            }
        )

    circular_seq = "".join(base for base in calls if base != "-")
    circular_name = f"{args.sample}_circular"
    write_fasta(outdir / f"{args.sample}.circular.consensus.fasta", circular_name, circular_seq)

    with (outdir / f"{args.sample}.depth.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(depth_rows[0].keys()), delimiter="\t")
        writer.writeheader()
        writer.writerows(depth_rows)

    covered_1x = sum(1 for depth in depths if depth >= 1)
    covered_10x = sum(1 for depth in depths if depth >= 10)
    covered_100x = sum(1 for depth in depths if depth >= 100)
    mean_depth = sum(depths) / len(depths)
    median_depth = statistics.median(depths)
    n_bases = circular_seq.count("N")

    coverage = {
        "genome_length": genome_length,
        "mean_depth": f"{mean_depth:.2f}",
        "median_depth": f"{median_depth:.2f}",
        "min_depth": min(depths),
        "max_depth": max(depths),
        "positions_covered_1x": covered_1x,
        "positions_covered_10x": covered_10x,
        "positions_covered_100x": covered_100x,
        "breadth_1x_pct": f"{100 * covered_1x / genome_length:.2f}",
        "breadth_10x_pct": f"{100 * covered_10x / genome_length:.2f}",
        "breadth_100x_pct": f"{100 * covered_100x / genome_length:.2f}",
        "consensus_length": len(circular_seq),
        "consensus_n_bases": n_bases,
        "consensus_deleted_bases": deletions,
        "reads_considered": stats["reads_considered"],
        "origin_spanning_reads": stats["origin_spanning_reads"],
    }
    with (outdir / f"{args.sample}.coverage.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["metric", "value"])
        writer.writerows(coverage.items())

    # Patch the viralrecon consensus where it is N but circular evidence is strong.
    patch_rows = []
    patch_status = "no_viralrecon_consensus"
    final_seq = circular_seq
    final_name = args.sample
    n_before = circular_seq.count("N")
    if args.viralrecon_consensus and Path(args.viralrecon_consensus).exists():
        vr_record = next(SeqIO.parse(args.viralrecon_consensus, "fasta"))
        vr_seq = str(vr_record.seq).upper()
        final_seq = vr_seq
        patch_status = "used_viralrecon"
        n_before = vr_seq.count("N")
        if len(vr_seq) == genome_length:
            patched = 0
            mismatches = 0
            for index, (vr_base, call) in enumerate(zip(vr_seq, calls), start=1):
                slot = counts[index - 1]
                depth = sum(slot.values())
                major_count = max(
                    slot.get("A", 0), slot.get("C", 0), slot.get("G", 0),
                    slot.get("T", 0), slot.get("del", 0),
                )
                fraction = major_count / depth if depth else 0.0
                if (
                    vr_base == "N"
                    and call in "ACGT"
                    and depth >= args.min_depth
                    and fraction >= args.min_allele_fraction
                ):
                    final_seq = final_seq[: index - 1] + call + final_seq[index:]
                    patched += 1
                    patch_rows.append(
                        [index, vr_base, call, depth, f"{fraction:.6f}", "patched_N"]
                    )
                elif (
                    vr_base in "ACGT"
                    and call in "ACGT"
                    and vr_base != call
                    and depth >= args.min_depth
                ):
                    mismatches += 1
                    patch_rows.append(
                        [index, vr_base, call, depth, f"{fraction:.6f}", "mismatch"]
                    )
            patch_status = f"used_viralrecon_patched_{patched}"
            coverage["viralrecon_mismatches"] = mismatches
            coverage["patched_n_positions"] = patched
        else:
            patch_status = "viralrecon_length_mismatch"
    final_seq = final_seq.upper()
    n_after = final_seq.count("N")
    write_fasta(outdir / f"{args.sample}.consensus.fasta", final_name, final_seq)

    coverage["consensus_source"] = patch_status
    coverage["final_length"] = len(final_seq)
    coverage["final_n_bases"] = n_after
    coverage["n_bases_before_patch"] = n_before
    coverage["n_bases_after_patch"] = n_after
    with (outdir / f"{args.sample}.coverage.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["metric", "value"])
        writer.writerows(coverage.items())

    with (outdir / f"{args.sample}.consensus_stats.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["sample", "genome_length", "consensus_length", "n_bases", "source"])
        writer.writerow([args.sample, genome_length, len(final_seq), n_after, patch_status])

    with (outdir / f"{args.sample}.boundary_patch.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow(["position", "viralrecon_base", "circular_base", "depth", "major_fraction", "action"])
        writer.writerows(patch_rows)

    print(
        f"{args.sample}: mean depth {mean_depth:.1f}x, breadth>=10x "
        f"{100 * covered_10x / genome_length:.1f}%, origin-spanning reads "
        f"{stats['origin_spanning_reads']}, consensus {len(final_seq)} bp, N={n_after}, "
        f"{patch_status}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
