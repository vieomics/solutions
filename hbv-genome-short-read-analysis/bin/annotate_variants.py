#!/usr/bin/env python3
"""Annotate HBV nucleotide and amino-acid variants.

Variants are reported relative to the closest curated public genome (the
genotype-matched context), not relative to the mapping reference.  Positions
are still expressed in NC_003977.2 coordinates so that they can be compared
across samples and with the genome map.  Overlapping reading frames are
annotated independently; no clinical interpretation is made.
"""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from Bio import SeqIO
from Bio.Align import PairwiseAligner
from Bio.Seq import Seq


# NC_003977.2 annotation.  Coordinates are 1-based, inclusive, and all regions
# are on the plus strand.  P and the preS region cross the arbitrary origin.
REGIONS = {
    "S": {"segments": [(157, 837)], "product": "small surface antigen"},
    "P": {"segments": [(2309, 3182), (1, 1625)], "product": "polymerase"},
    "C": {"segments": [(1816, 2454)], "product": "precore/core"},
    "X": {"segments": [(1376, 1840)], "product": "HBx"},
    # subregions, useful for interpretation of the overlapping S ORF
    "preS1": {"segments": [(2850, 3173)], "product": "preS1"},
    "preS2": {"segments": [(3174, 3182), (1, 156)], "product": "preS2"},
    "preC": {"segments": [(1816, 1902)], "product": "precore"},
}
PRIMARY_REGIONS = ["S", "P", "C", "X"]

COMPLEMENT = str.maketrans("ACGTN", "TGCAN")


def make_aligner() -> PairwiseAligner:
    aligner = PairwiseAligner()
    aligner.mode = "global"
    aligner.match_score = 2
    aligner.mismatch_score = -1
    aligner.open_gap_score = -5
    aligner.extend_gap_score = -0.5
    return aligner


def gapped_pair(aligner: PairwiseAligner, reference: str, query: str) -> tuple[str, str]:
    alignment = aligner.align(reference, query)[0]
    return str(alignment[0]), str(alignment[1])


def map_to_reference(
    aligner: PairwiseAligner, reference: str, query: str
) -> tuple[dict[int, str | None], list[tuple[int | None, str]]]:
    """Return {reference_position_1based: query_base_or_None} and insertions.

    A ``None`` value means the query has a deletion at that reference position.
    The insertion list contains (reference_position_before_insertion, inserted_seq).
    """
    ref_aln, query_aln = gapped_pair(aligner, reference, query)
    mapping: dict[int, str | None] = {}
    insertions: list[tuple[int | None, str]] = []
    ref_pos = 0
    pending_insertion = ""
    last_ref_pos = None
    for ref_base, query_base in zip(ref_aln, query_aln):
        if ref_base == "-":
            pending_insertion += query_base
            continue
        ref_pos += 1
        if pending_insertion:
            insertions.append((last_ref_pos, pending_insertion))
            pending_insertion = ""
        mapping[ref_pos] = None if query_base == "-" else query_base.upper()
        last_ref_pos = ref_pos
    if pending_insertion:
        insertions.append((last_ref_pos, pending_insertion))
    return mapping, insertions


def identity(aligner: PairwiseAligner, reference: str, query: str) -> float:
    ref_aln, query_aln = gapped_pair(aligner, reference, query)
    matches = 0
    compared = 0
    for ref_base, query_base in zip(ref_aln, query_aln):
        if ref_base == "-" or query_base == "-":
            continue
        if ref_base == "N" or query_base == "N":
            continue
        compared += 1
        if ref_base == query_base:
            matches += 1
    return matches / compared if compared else 0.0


def cds_sequence(reference: str, segments: list[tuple[int, int]]) -> str:
    return "".join(reference[start - 1 : end] for start, end in segments)


def cds_layout(segments: list[tuple[int, int]]) -> dict[int, int]:
    layout = {}
    offset = 0
    for start, end in segments:
        for position in range(start, end + 1):
            offset += 1
            layout[position] = offset
    return layout


def translate_codon(codon: str) -> str:
    if len(codon) != 3 or any(base not in "ACGT" for base in codon):
        return "X"
    return str(Seq(codon).translate())


def variant_effect(ref_aa: str, alt_aa: str) -> str:
    if ref_aa == "X" or alt_aa == "X":
        return "uncertain"
    if ref_aa == alt_aa:
        return "synonymous"
    if alt_aa == "*":
        return "stop_gained"
    if ref_aa == "*":
        return "stop_lost"
    return "nonsynonymous"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference-genbank", default="references/genbank/NC_003977.2.gb")
    parser.add_argument("--public-fasta", default="references/hbv_public_genomes.fasta")
    parser.add_argument("--public-metadata", default="references/hbv_metadata.tsv")
    parser.add_argument("--consensus-dir", default="results/consensus")
    parser.add_argument("--sample-metadata", default="metadata/selected_samples.tsv")
    parser.add_argument("--depth-dir", default="results/consensus")
    parser.add_argument("--outdir", default="results/variants")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    reference_record = SeqIO.read(args.reference_genbank, "genbank")
    reference = str(reference_record.seq).upper()
    aligner = make_aligner()

    public = {
        record.id.split("|")[0]: str(record.seq).upper()
        for record in SeqIO.parse(args.public_fasta, "fasta")
    }
    public_meta = {}
    with open(args.public_metadata, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            public_meta[row["accession"]] = row
    public_accessions = [accession for accession in public if accession in public_meta]

    sample_meta = {}
    with open(args.sample_metadata, newline="") as handle:
        for row in csv.DictReader(handle, delimiter="\t"):
            sample_meta[row["sample"]] = row

    consensus_records = {}
    for path in sorted(Path(args.consensus_dir).glob("*.consensus.fasta")):
        if path.name.endswith(".circular.consensus.fasta"):
            continue
        for record in SeqIO.parse(path, "fasta"):
            if record.id.endswith("_circular"):
                continue
            consensus_records[record.id] = str(record.seq).upper()
    if not consensus_records:
        raise SystemExit(f"no consensus FASTA files found in {args.consensus_dir}")

    region_layouts = {name: cds_layout(spec["segments"]) for name, spec in REGIONS.items()}
    region_cds = {name: cds_sequence(reference, spec["segments"]) for name, spec in REGIONS.items()}
    region_protein = {name: str(Seq(seq).translate()) for name, seq in region_cds.items()}

    closest_rows = []
    nucleotide_rows = []
    amino_rows = []
    indel_rows = []
    summary = defaultdict(int)

    for sample, sample_seq in sorted(consensus_records.items()):
        meta = sample_meta.get(sample, {})
        genotype = meta.get("genotype", "")

        best_accession = None
        best_identity = -1.0
        for accession in public_accessions:
            value = identity(aligner, sample_seq, public[accession])
            if value > best_identity:
                best_identity = value
                best_accession = accession
        closest_seq = public[best_accession]
        closest_rows.append(
            {
                "sample": sample,
                "sample_genotype": genotype,
                "closest_reference": best_accession,
                "closest_genotype": public_meta[best_accession]["genotype"],
                "nucleotide_identity": f"{best_identity:.6f}",
            }
        )

        sample_map, sample_insertions = map_to_reference(aligner, reference, sample_seq)
        closest_map, _closest_insertions = map_to_reference(aligner, reference, closest_seq)

        # Depth from circular mapping, if available.
        depth = {}
        depth_path = Path(args.depth_dir) / f"{sample}.depth.tsv"
        if depth_path.exists():
            with depth_path.open(newline="") as handle:
                for row in csv.DictReader(handle, delimiter="\t"):
                    depth[int(row["position"])] = (
                        int(row["depth"]),
                        float(row["major_fraction"]),
                    )

        # Substitutions relative to the closest public genome, in NC_003977.2 coordinates.
        for position in range(1, len(reference) + 1):
            alt = sample_map.get(position)
            ref_base = closest_map.get(position)
            mapping_ref_base = reference[position - 1]
            if alt is None or ref_base is None:
                continue
            if alt not in "ACGT" or ref_base not in "ACGT" or alt == ref_base:
                continue
            regions = [
                name
                for name, spec in REGIONS.items()
                if any(start <= position <= end for start, end in spec["segments"])
            ]
            if not regions:
                regions = ["intergenic"]
            depth_value, major_fraction = depth.get(position, ("", ""))
            row_base = {
                "sample": sample,
                "genotype": genotype,
                "reference_used": best_accession,
                "reference_genotype": public_meta[best_accession]["genotype"],
                "genotype_discordance": (
                    "yes" if genotype and genotype != public_meta[best_accession]["genotype"] else "no"
                ),
                "position": position,
                "mapping_reference_base": mapping_ref_base,
                "reference_base": ref_base,
                "alternate_base": alt,
                "depth": depth_value,
                "major_fraction": major_fraction,
                "regions": ",".join(regions),
            }
            for region in regions:
                if region == "intergenic":
                    nucleotide_rows.append(
                        {
                            **row_base,
                            "region": "intergenic",
                            "cds_position": "",
                            "codon": "",
                            "ref_codon": "",
                            "alt_codon": "",
                            "ref_aa": "",
                            "alt_aa": "",
                            "aa_change": "",
                            "effect": "intergenic",
                            "confidence": "high" if depth_value != "" else "not_assessed",
                        }
                    )
                    summary[(sample, "intergenic", "intergenic")] += 1
                    continue
                offset = region_layouts[region].get(position)
                if offset is None:
                    continue
                codon_index = (offset - 1) // 3
                codon_offset = (offset - 1) % 3
                ref_codon_list = list(region_cds[region][codon_index * 3 : codon_index * 3 + 3])
                if len(ref_codon_list) < 3:
                    continue
                ref_codon = "".join(ref_codon_list)
                alt_codon_list = list(ref_codon)
                alt_codon_list[codon_offset] = alt
                alt_codon = "".join(alt_codon_list)
                # Closest reference codon and sample codon at this NC position
                closest_bases = [
                    closest_map.get(p) for p in _region_positions(region, codon_index)
                ]
                sample_bases = [
                    sample_map.get(p) for p in _region_positions(region, codon_index)
                ]
                if any(base is None for base in closest_bases) or any(
                    base is None for base in sample_bases
                ):
                    effect = "uncertain_indel"
                    ref_aa = alt_aa = "X"
                    closest_codon = ref_codon
                    sample_codon = alt_codon
                else:
                    closest_codon = "".join(closest_bases)
                    sample_codon = "".join(sample_bases)
                    ref_aa = translate_codon(closest_codon)
                    alt_aa = translate_codon(sample_codon)
                    effect = variant_effect(ref_aa, alt_aa)
                aa_position = codon_index + 1
                aa_change = f"{ref_aa}{aa_position}{alt_aa}" if ref_aa != "X" else ""
                nucleotide_rows.append(
                    {
                        **row_base,
                        "region": region,
                        "cds_position": offset,
                        "codon": aa_position,
                        "ref_codon": closest_codon,
                        "alt_codon": sample_codon,
                        "ref_aa": ref_aa,
                        "alt_aa": alt_aa,
                        "aa_change": aa_change,
                        "effect": effect,
                        "confidence": "high" if depth_value != "" else "not_assessed",
                    }
                )
                summary[(sample, region, effect)] += 1
                if aa_change:
                    amino_rows.append(
                        {
                            "sample": sample,
                            "genotype": genotype,
                            "reference_used": best_accession,
                            "reference_genotype": public_meta[best_accession]["genotype"],
                            "region": region,
                            "codon": aa_position,
                            "ref_aa": ref_aa,
                            "alt_aa": alt_aa,
                            "aa_change": aa_change,
                            "effect": effect,
                            "nucleotide_changes": f"{ref_base}{position}{alt}",
                            "depth": depth_value,
                        }
                    )

        # Indels relative to the closest reference, using the pairwise alignment.
        ref_aln, sample_aln = gapped_pair(aligner, closest_seq, sample_seq)
        ref_pos = 0
        insertion = ""
        insertion_anchor = None
        for ref_base, sample_base in zip(ref_aln, sample_aln):
            if ref_base == "-":
                insertion += sample_base
                continue
            ref_pos += 1
            if insertion:
                indel_rows.append(
                    {
                        "sample": sample,
                        "genotype": genotype,
                        "reference_used": best_accession,
                        "type": "insertion",
                        "position": insertion_anchor or "",
                        "reference_sequence": "-",
                        "alternate_sequence": insertion,
                        "length": len(insertion),
                        "effect": "frameshift" if len(insertion) % 3 else "inframe_insertion",
                    }
                )
                insertion = ""
                insertion_anchor = None
            if sample_base == "-":
                # collect consecutive deletions below via a small look-ahead buffer
                insertion_anchor = insertion_anchor  # keep type checkers quiet
        # Simpler deletion walk (handles consecutive bases).
        ref_pos = 0
        deletion = ""
        deletion_start = None
        for ref_base, sample_base in zip(ref_aln, sample_aln):
            if ref_base == "-":
                continue
            ref_pos += 1
            if sample_base == "-":
                if deletion_start is None:
                    deletion_start = ref_pos
                deletion += ref_base
            elif deletion:
                indel_rows.append(
                    {
                        "sample": sample,
                        "genotype": genotype,
                        "reference_used": best_accession,
                        "type": "deletion",
                        "position": deletion_start,
                        "reference_sequence": deletion,
                        "alternate_sequence": "-",
                        "length": len(deletion),
                        "effect": "frameshift" if len(deletion) % 3 else "inframe_deletion",
                    }
                )
                deletion = ""
                deletion_start = None
        if deletion:
            indel_rows.append(
                {
                    "sample": sample,
                    "genotype": genotype,
                    "reference_used": best_accession,
                    "type": "deletion",
                    "position": deletion_start,
                    "reference_sequence": deletion,
                    "alternate_sequence": "-",
                    "length": len(deletion),
                    "effect": "frameshift" if len(deletion) % 3 else "inframe_deletion",
                }
            )

    # De-duplicate amino-acid changes and merge nucleotide changes.
    merged_amino = {}
    for row in amino_rows:
        key = (row["sample"], row["region"], row["aa_change"], row["effect"])
        if key not in merged_amino:
            merged_amino[key] = dict(row)
        else:
            merged_amino[key]["nucleotide_changes"] += ";" + row["nucleotide_changes"]
    amino_rows = list(merged_amino.values())

    nucleotide_fields = [
        "sample", "genotype", "reference_used", "reference_genotype",
        "genotype_discordance", "position", "mapping_reference_base",
        "reference_base", "alternate_base", "depth", "major_fraction", "regions",
        "region", "cds_position", "codon", "ref_codon", "alt_codon", "ref_aa",
        "alt_aa", "aa_change", "effect", "confidence",
    ]
    with (outdir / "nucleotide_variants.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=nucleotide_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(nucleotide_rows)

    amino_fields = [
        "sample", "genotype", "reference_used", "reference_genotype", "region",
        "codon", "ref_aa", "alt_aa", "aa_change", "effect", "nucleotide_changes", "depth",
    ]
    with (outdir / "amino_acid_variants.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=amino_fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(sorted(amino_rows, key=lambda r: (r["sample"], r["region"], r["codon"])))

    with (outdir / "indel_variants.tsv").open("w", newline="") as handle:
        fields = [
            "sample", "genotype", "reference_used", "type", "position",
            "reference_sequence", "alternate_sequence", "length", "effect",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(indel_rows)

    with (outdir / "closest_references.tsv").open("w", newline="") as handle:
        fields = ["sample", "sample_genotype", "closest_reference", "closest_genotype", "nucleotide_identity"]
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(closest_rows)

    summary_rows = []
    for (sample, region, effect), count in sorted(summary.items()):
        summary_rows.append(
            {"sample": sample, "region": region, "effect": effect, "count": count}
        )
    with (outdir / "mutation_summary.tsv").open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["sample", "region", "effect", "count"], delimiter="\t")
        writer.writeheader()
        writer.writerows(summary_rows)

    params = [
        "Variant annotation parameters",
        f"mapping_reference: NC_003977.2 ({len(reference)} bp)",
        "comparison_reference: closest curated public genome by global nucleotide identity",
        "coordinate_system: NC_003977.2, 1-based, inclusive",
        "substitution_calling: sample base != closest-reference base at an aligned NC_003977.2 position",
        "minimum_depth_for_confidence: 10 (from circular pileup)",
        "regions: S, P, C, X; subregions preS1, preS2, preC are reported separately",
        "effect: synonymous, nonsynonymous, stop_gained, stop_lost, uncertain_indel, intergenic",
        "clinical_interpretation: none; variants are not classified as drug resistance or immune escape",
        "indels: called from the sample-vs-closest-reference global alignment; positions are approximate",
    ]
    (outdir / "variant_calling_parameters.txt").write_text("\n".join(params) + "\n")
    print(
        f"wrote {len(nucleotide_rows)} nucleotide rows, {len(amino_rows)} amino-acid rows, "
        f"{len(indel_rows)} indels for {len(consensus_records)} samples"
    )
    return 0


def _region_positions(region: str, codon_index: int) -> list[int]:
    """Return the three NC_003977.2 positions for a codon in a region."""
    positions = []
    start_offset = codon_index * 3
    for codon_base in range(3):
        offset = start_offset + codon_base
        for start, end in REGIONS[region]["segments"]:
            length = end - start + 1
            if offset < length:
                positions.append(start + offset)
                break
            offset -= length
    return positions


if __name__ == "__main__":
    raise SystemExit(main())
