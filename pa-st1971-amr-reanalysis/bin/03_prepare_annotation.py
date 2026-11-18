#!/usr/bin/env python3
"""Step 3 - turn the deposited GenBank annotation into proteins + GFF3.

The paper used Bakta 1.10.3. Bakta's light database is still a 1.5 GB download,
which is a poor first experience for a beginner and is not available in the
public OmicsLab database workspace. The authors already deposited a fully
annotated GenBank record with the chromosome, so this script reuses that
annotation: it writes the same two files AMRFinderPlus needs (a protein FASTA
and a GFF3) without a second annotation run.

Input : data/CP196749.1.gbff
Output: results/annotation/strain71.faa
        results/annotation/strain71.gff3
        results/annotation/annotation_summary.tsv

If you want to reproduce the paper's Bakta annotation exactly, run
`ANNOTATION_SOURCE=bakta bash bin/03_annotate.sh` instead. That mode downloads
the Bakta light database and uses Bakta 1.10.3.
"""
from __future__ import annotations

import csv
from pathlib import Path
from urllib.parse import quote

from Bio import SeqIO

ROOT = Path(__file__).resolve().parent.parent
GBFF = ROOT / "data" / "CP196749.1.gbff"
FASTA = ROOT / "data" / "CP196749.1.fasta"
OUTDIR = ROOT / "results" / "annotation"


def first(values: list[str] | None, default: str = "") -> str:
    return values[0] if values else default


def gff_value(value: str) -> str:
    """Escape the characters that have special meaning in GFF3 attributes."""
    return quote(value.replace("\t", " "), safe=" /:,.-_()[]+*'&%#@")


def main() -> None:
    if not GBFF.is_file():
        raise SystemExit(f"Missing {GBFF}; run bin/01_download_genome.sh first")

    OUTDIR.mkdir(parents=True, exist_ok=True)
    record = SeqIO.read(GBFF, "genbank")
    # The GFF seqid must match the first token of the FASTA header, which is
    # not always the GenBank accession (ENA mirrors use ENA|ACC|VERSION).
    contig_id = SeqIO.read(FASTA, "fasta").id
    faa_path = OUTDIR / "strain71.faa"
    gff_path = OUTDIR / "strain71.gff3"

    proteins: list[tuple[str, str]] = []
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for feature in record.features:
        if feature.type != "CDS":
            continue
        qualifiers = feature.qualifiers
        translation = first(qualifiers.get("translation"))
        if not translation:
            # Pseudo/partial CDS without a deposited translation.
            continue

        locus_tag = first(qualifiers.get("locus_tag"))
        protein_id = first(qualifiers.get("protein_id"))
        gene = first(qualifiers.get("gene"))
        product = first(qualifiers.get("product"))
        ident = locus_tag or protein_id or f"cds_{len(rows) + 1}"
        if ident in seen_ids:
            ident = f"{ident}_{len(rows) + 1}"
        seen_ids.add(ident)

        start = int(feature.location.start) + 1
        end = int(feature.location.end)
        strand = "+" if feature.location.strand == 1 else "-"
        codon_start = int(first(qualifiers.get("codon_start"), "1"))
        phase = codon_start - 1
        if strand == "-":
            # For a reverse-strand CDS, GFF phase is measured from the end.
            phase = (3 - ((end - start + 1 - phase) % 3)) % 3

        # AMRFinderPlus matches protein FASTA ids against the GFF `Name`
        # attribute (not `ID`), so keep the same identifier in both files.
        attributes = [
            f"ID={gff_value(ident)}",
            f"Name={gff_value(ident)}",
        ]
        if locus_tag:
            attributes.append(f"locus_tag={gff_value(locus_tag)}")
        if gene:
            attributes.append(f"gene={gff_value(gene)}")
        if product:
            attributes.append(f"product={gff_value(product)}")
        if protein_id:
            attributes.append(f"protein_id={gff_value(protein_id)}")

        proteins.append((ident, translation))
        rows.append(
            {
                "id": ident,
                "gene": gene,
                "protein_id": protein_id,
                "product": product,
                "start": str(start),
                "end": str(end),
                "strand": strand,
                "gff": "\t".join(
                    [
                        contig_id,
                        "GenBank",
                        "CDS",
                        str(start),
                        str(end),
                        ".",
                        strand,
                        str(phase),
                        ";".join(attributes),
                    ]
                ),
            }
        )

    if not proteins:
        raise SystemExit(f"No translated CDS features found in {GBFF}")

    with faa_path.open("w") as handle:
        for ident, translation in proteins:
            handle.write(f">{ident}\n")
            for offset in range(0, len(translation), 60):
                handle.write(translation[offset : offset + 60] + "\n")

    with gff_path.open("w") as handle:
        handle.write("##gff-version 3\n")
        for row in rows:
            handle.write(row["gff"] + "\n")

    with (OUTDIR / "annotation_summary.tsv").open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t", lineterminator="\n")
        writer.writerow(["metric", "value"])
        writer.writerow(["source", "GenBank flat file (authors' deposited annotation)"])
        writer.writerow(["accession", record.id])
        writer.writerow(["description", record.description])
        writer.writerow(["cds_with_translation", str(len(proteins))])
        writer.writerow(["protein_fasta", str(faa_path.relative_to(ROOT))])
        writer.writerow(["gff3", str(gff_path.relative_to(ROOT))])
        writer.writerow(["note", "Bakta mode is optional; see results/README.md"])

    print(f"[annotation] {len(proteins)} translated CDS from {GBFF.name}")
    print(f"[annotation] wrote {faa_path.relative_to(ROOT)}")
    print(f"[annotation] wrote {gff_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
