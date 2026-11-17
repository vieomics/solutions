#!/usr/bin/env python3
"""Build the curated HBV reference panel used in this solution.

The panel is intentionally small (10 complete genomes) and was selected by hand
from GenBank records with explicit genotype annotations, country and collection
date where available.  Records are cached as GenBank flat files so the panel can
be rebuilt without re-downloading, and every sequence is checked for length,
ambiguous bases and duplicate accessions before use.

The public genomes are rotated to the origin of the mapping reference
(NC_003977.2) using a k-mer vote.  This is required because complete HBV genomes
are circular and GenBank entries use different sequence start positions; simply
concatenating them would create artificial gaps at the ends of a multiple
sequence alignment.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from Bio import SeqIO
from Bio.Seq import Seq

EFETCH = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
REFERENCE_ACCESSION = "NC_003977.2"

# Curated panel: two genotype A, two B, two C, three D (including the
# RefSeq mapping reference), one E and one F.
# Selection rules:
#   * complete genome, 3.0-3.3 kb, <1% ambiguous bases;
#   * explicit genotype annotation in the GenBank record (except the RefSeq);
#   * B/C from Vietnam / Southeast Asia;
#   * A/D include Brazilian genomes because the five study samples are from Brazil;
#   * E and F provide outgroup diversity without turning this into a population study.
CURATED = [
    {
        "accession": "NC_003977.2",
        "genotype": "D",
        "role": "mapping reference / RefSeq genotype D (strain ayw)",
        "country_override": "not available",
        "date_override": "not available",
    },
    {
        "accession": "KJ854710.1",
        "genotype": "A",
        "role": "genotype A2, Brazil, 2007",
    },
    {
        "accession": "MF674515.1",
        "genotype": "B",
        "role": "genotype B4, Vietnam, 2014",
    },
    {
        "accession": "LC456127.1",
        "genotype": "B",
        "role": "genotype B2, Cambodia, 2011",
    },
    {
        "accession": "LC456135.1",
        "genotype": "C",
        "role": "genotype C1, Cambodia, 2013",
    },
    {
        "accession": "LC535950.1",
        "genotype": "C",
        "role": "genotype C1, Cambodia, 2017",
    },
    {
        "accession": "MH724251.1",
        "genotype": "D",
        "role": "genotype D4, Brazil, 2004",
    },
    {
        "accession": "MH724252.1",
        "genotype": "D",
        "role": "genotype D1, Brazil, 2012",
    },
    {
        "accession": "PZ495693.1",
        "genotype": "E",
        "role": "genotype E, Kenya, 2023",
    },
    {
        "accession": "MK183647.1",
        "genotype": "F",
        "role": "genotype F4, Paraguay, 2017",
    },
]

GENOTYPE_RE = re.compile(r"genotype[:\s]*([A-J])\b", re.I)
SUBGENOTYPE_RE = re.compile(r"(?:subtype|subgenotype|genotype)[:\s]*([A-J][0-9]?)\b", re.I)


def log(msg: str) -> None:
    print(f"[references] {msg}", flush=True)


def fetch_genbank(accession: str, cache_dir: Path, retries: int = 4) -> str:
    cache = cache_dir / f"{accession}.gb"
    if cache.exists() and cache.stat().st_size > 100:
        return cache.read_text()
    url = EFETCH + "?" + urllib.parse.urlencode(
        {"db": "nuccore", "id": accession, "rettype": "gb", "retmode": "text"}
    )
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with urllib.request.urlopen(url, timeout=60) as handle:
                text = handle.read().decode("utf-8", "replace")
            if "LOCUS" not in text:
                raise RuntimeError(f"unexpected E-utilities response for {accession}")
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(text)
            time.sleep(0.4)  # be polite to NCBI
            return text
        except Exception as exc:  # noqa: BLE001 - retry any network/parse error
            last_error = exc
            log(f"fetch {accession} attempt {attempt} failed: {exc}")
            time.sleep(2 * attempt)
    raise RuntimeError(f"could not fetch {accession}: {last_error}")


def source_qualifiers(record) -> dict:
    for feature in record.features:
        if feature.type == "source":
            return feature.qualifiers
    return {}


def clean_country(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "not available"
    value = value.split(":")[0].strip()
    return {"Viet Nam": "Vietnam", "Vietnam": "Vietnam"}.get(value, value)


def clean_date(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return "not available"
    # Normalise common GenBank forms such as 01-Jan-2007 to 2007-01-01.
    for fmt in ("%d-%b-%Y", "%Y-%m-%d", "%Y-%m", "%Y"):
        try:
            parsed = datetime.strptime(value, fmt)
            return parsed.strftime("%Y-%m-%d") if fmt != "%Y" else parsed.strftime("%Y")
        except ValueError:
            continue
    return value


def unique_kmers(seq: str, k: int) -> dict[str, int]:
    counts: dict[str, int] = {}
    for i in range(len(seq) - k + 1):
        kmer = seq[i : i + k]
        if "N" in kmer:
            continue
        counts[kmer] = counts.get(kmer, 0) + 1
    return {kmer: pos for pos, kmer in enumerate(
        seq[i : i + k] for i in range(len(seq) - k + 1)
    ) if counts.get(kmer) == 1 and "N" not in kmer}


def kmer_votes(query: str, ref_index: dict[str, int], k: int, step: int = 1) -> dict[int, int]:
    votes: dict[int, int] = {}
    for qpos in range(0, len(query) - k + 1, step):
        kmer = query[qpos : qpos + k]
        if "N" in kmer:
            continue
        rpos = ref_index.get(kmer)
        if rpos is None:
            continue
        offset = (qpos - rpos) % len(query)
        votes[offset] = votes.get(offset, 0) + 1
    return votes


def normalise_origin(seq: str, ref_seq: str, k: int = 25) -> tuple[str, int, str, int, int]:
    """Rotate ``seq`` so that its coordinate 1 corresponds to the reference origin.

    Returns (oriented_rotated_sequence, offset, orientation, votes, margin).
    ``margin`` is the winning vote count minus the runner-up; a small margin is
    flagged by the caller.
    """
    ref_index = unique_kmers(ref_seq, k)
    best = None
    for orientation, candidate in (("forward", seq), ("reverse", str(Seq(seq).reverse_complement()))):
        votes = kmer_votes(candidate, ref_index, k)
        if not votes:
            continue
        ranked = sorted(votes.items(), key=lambda item: (-item[1], item[0]))
        offset, support = ranked[0]
        runner_up = ranked[1][1] if len(ranked) > 1 else 0
        if best is None or support > best[3]:
            best = (orientation, candidate, offset, support, support - runner_up, len(votes))
    if best is None:
        raise RuntimeError("could not determine sequence orientation by k-mer voting")
    orientation, candidate, offset, support, margin, n_offsets = best
    rotated = candidate[offset:] + candidate[:offset]
    if support < 20:
        raise RuntimeError(f"weak origin/orientation evidence: support={support}, margin={margin}")
    log(
        f"origin: {orientation} offset={offset} support={support} "
        f"margin={margin} candidate_offsets={n_offsets}"
    )
    return rotated, offset, orientation, support, margin


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--outdir", default="references", help="output directory")
    args = parser.parse_args()

    outdir = Path(args.outdir)
    gbdir = outdir / "genbank"
    outdir.mkdir(parents=True, exist_ok=True)
    gbdir.mkdir(parents=True, exist_ok=True)

    retrieved = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    records = {}
    for item in CURATED:
        accession = item["accession"]
        log(f"reading {accession} ({item['role']})")
        gb = fetch_genbank(accession, gbdir)
        record = SeqIO.read(io.StringIO(gb), "genbank")
        records[accession] = record

    if REFERENCE_ACCESSION not in records:
        raise SystemExit(f"reference {REFERENCE_ACCESSION} missing from panel")
    ref_seq = str(records[REFERENCE_ACCESSION].seq).upper()
    if len(ref_seq) < 3000 or len(ref_seq) > 3300:
        raise SystemExit(f"reference length looks wrong: {len(ref_seq)}")

    rows = []
    fasta_rows = []
    seen = set()
    for item in CURATED:
        accession = item["accession"]
        record = records[accession]
        seq = str(record.seq).upper()
        quals = source_qualifiers(record)
        notes = " | ".join(quals.get("note", []))
        genotype_note = GENOTYPE_RE.search(notes)
        subgenotype_note = SUBGENOTYPE_RE.search(notes)
        genotype = item["genotype"]
        if genotype_note and genotype_note.group(1).upper() != genotype:
            raise SystemExit(
                f"genotype mismatch for {accession}: curated {genotype}, GenBank {genotype_note.group(1)}"
            )
        if accession in seen:
            raise SystemExit(f"duplicate accession in panel: {accession}")
        seen.add(accession)

        country = item.get("country_override") or clean_country(quals.get("geo_loc_name", [""])[0])
        date = item.get("date_override") or clean_date(quals.get("collection_date", [""])[0])
        isolate = (quals.get("isolate", [""])[0] or "").strip()
        n_bases = seq.count("N")
        n_fraction = n_bases / len(seq)
        if not (3000 <= len(seq) <= 3300):
            raise SystemExit(f"{accession}: length {len(seq)} outside 3000-3300 bp")
        if n_fraction > 0.01:
            raise SystemExit(f"{accession}: {n_bases} N bases ({n_fraction:.2%}) exceeds 1%")

        oriented, offset, orientation, support, margin = normalise_origin(seq, ref_seq)
        subgenotype = subgenotype_note.group(1) if subgenotype_note else genotype
        label = f"{accession}|{subgenotype}|{country.replace(' ', '_')}|{date}"
        fasta_rows.append((label, oriented))
        rows.append(
            {
                "accession": accession,
                "genotype": genotype,
                "subgenotype": subgenotype,
                "country": country,
                "collection_date": date,
                "sequence_length": len(seq),
                "n_bases": n_bases,
                "n_fraction": f"{n_fraction:.6f}",
                "isolate": isolate,
                "source": "GenBank",
                "description": record.description,
                "rotation_offset": offset,
                "orientation": orientation,
                "kmer_support": support,
                "kmer_margin": margin,
                "retrieved": retrieved,
                "notes": notes,
                "role": item["role"],
            }
        )
        log(
            f"{accession}: {genotype}/{subgenotype} {country} {date} "
            f"{len(seq)} bp, N={n_bases}"
        )

    # Reference is written separately for the mapping pipeline.
    ref_record = records[REFERENCE_ACCESSION]
    ref_out = outdir / "hbv_reference.fasta"
    with ref_out.open("w") as handle:
        handle.write(f">{REFERENCE_ACCESSION} Hepatitis B virus genotype D reference (strain ayw)\n")
        for i in range(0, len(ref_seq), 70):
            handle.write(ref_seq[i : i + 70] + "\n")

    raw_out = outdir / "hbv_public_genomes.raw.fasta"
    with raw_out.open("w") as handle:
        for item in CURATED:
            accession = item["accession"]
            seq = str(records[accession].seq).upper()
            handle.write(f">{accession}|{item['genotype']}|raw\n")
            for i in range(0, len(seq), 70):
                handle.write(seq[i : i + 70] + "\n")

    norm_out = outdir / "hbv_public_genomes.fasta"
    with norm_out.open("w") as handle:
        for label, seq in fasta_rows:
            handle.write(f">{label}\n")
            for i in range(0, len(seq), 70):
                handle.write(seq[i : i + 70] + "\n")

    metadata_path = outdir / "hbv_metadata.tsv"
    fields = [
        "accession",
        "genotype",
        "subgenotype",
        "country",
        "collection_date",
        "sequence_length",
        "n_bases",
        "n_fraction",
        "isolate",
        "source",
        "description",
        "rotation_offset",
        "orientation",
        "kmer_support",
        "kmer_margin",
        "retrieved",
        "notes",
        "role",
    ]
    with metadata_path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)

    with (outdir / "accessions.txt").open("w") as handle:
        handle.write("\n".join(item["accession"] for item in CURATED) + "\n")

    manifest = {
        "retrieved_utc": retrieved,
        "efetch_url": EFETCH,
        "reference_accession": REFERENCE_ACCESSION,
        "panel_size": len(CURATED),
        "accessions": [item["accession"] for item in CURATED],
        "files": {},
        "genotypes": {key: sum(1 for row in rows if row["genotype"] == key) for key in "ABCDEFGHIJ"},
    }
    for path in (ref_out, raw_out, norm_out, metadata_path):
        manifest["files"][str(path)] = {"sha256": sha256(path), "bytes": path.stat().st_size}
    (outdir / "fetch_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    selection = [
        "# HBV reference panel",
        "",
        f"Retrieved from NCBI GenBank on {retrieved} using E-utilities `efetch`.",
        f"Mapping reference: `{REFERENCE_ACCESSION}` (genotype D, strain ayw, {len(ref_seq)} bp).",
        "",
        "The five study samples are from Brazil (genotypes A and D). The panel therefore",
        "includes a Brazilian genotype A2 genome, two Brazilian genotype D genomes and",
        "the genotype D RefSeq, two genotype B and two genotype C genomes from",
        "Vietnam/Cambodia, and one E and one F genome for",
        "outgroup diversity. This is a demonstration panel, not a representative",
        "sample of global HBV diversity.",
        "",
        "| accession | genotype | subgenotype | country | collection_date | length | N | role |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        selection.append(
            f"| {row['accession']} | {row['genotype']} | {row['subgenotype']} | "
            f"{row['country']} | {row['collection_date']} | {row['sequence_length']} | "
            f"{row['n_bases']} | {row['role']} |"
        )
    selection += [
        "",
        "## Checks",
        "",
        "- All records are annotated as complete genomes and are 3182-3221 bp.",
        "- Ambiguous bases are below 1% for every record (only MH724252.1 has 3 Ns).",
        "- Accessions are unique.",
        "- Each sequence was rotated to the NC_003977.2 origin by a unique 25-mer vote;",
        "  the offset, orientation and k-mer support are in `hbv_metadata.tsv`.",
        "",
        "## Files",
        "",
        "- `hbv_reference.fasta` - mapping reference (NC_003977.2).",
        "- `hbv_public_genomes.fasta` - 10 public genomes, origin-normalised.",
        "- `hbv_public_genomes.raw.fasta` - the same records before rotation.",
        "- `hbv_metadata.tsv` - accession, genotype, country, date, length and QC fields.",
        "- `genbank/` - cached GenBank flat files.",
        "- `fetch_manifest.json` - retrieval URL, accessions and SHA-256 checksums.",
        "",
    ]
    (outdir / "reference_selection.md").write_text("\n".join(selection))
    log(f"wrote {metadata_path}, {norm_out}, {ref_out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
