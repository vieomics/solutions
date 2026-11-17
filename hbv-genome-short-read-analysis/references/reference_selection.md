# HBV reference panel

Retrieved from NCBI GenBank on 2026-11-17 using E-utilities `efetch`.
Mapping reference: `NC_003977.2` (genotype D, strain ayw, 3182 bp).

The five study samples are from Brazil (genotypes A and D). The panel therefore
includes a Brazilian genotype A2 genome, two Brazilian genotype D genomes and
the genotype D RefSeq, two genotype B and two genotype C genomes from
Vietnam/Cambodia, and one E and one F genome for
outgroup diversity. This is a demonstration panel, not a representative
sample of global HBV diversity.

| accession | genotype | subgenotype | country | collection_date | length | N | role |
|---|---|---|---|---|---|---|---|
| NC_003977.2 | D | D | not available | not available | 3182 | 0 | mapping reference / RefSeq genotype D (strain ayw) |
| KJ854710.1 | A | A2 | Brazil | 2007-01-01 | 3221 | 0 | genotype A2, Brazil, 2007 |
| MF674515.1 | B | B4 | Vietnam | 2014-06-19 | 3215 | 0 | genotype B4, Vietnam, 2014 |
| LC456127.1 | B | B2 | Cambodia | 2011 | 3215 | 0 | genotype B2, Cambodia, 2011 |
| LC456135.1 | C | C1 | Cambodia | 2013 | 3215 | 0 | genotype C1, Cambodia, 2013 |
| LC535950.1 | C | C1 | Cambodia | 2017 | 3215 | 0 | genotype C1, Cambodia, 2017 |
| MH724251.1 | D | D4 | Brazil | 2004 | 3182 | 0 | genotype D4, Brazil, 2004 |
| MH724252.1 | D | D1 | Brazil | 2012 | 3182 | 3 | genotype D1, Brazil, 2012 |
| PZ495693.1 | E | E | Kenya | 2023 | 3212 | 0 | genotype E, Kenya, 2023 |
| MK183647.1 | F | F4 | Paraguay | 2017 | 3215 | 0 | genotype F4, Paraguay, 2017 |

## Checks

- All records are annotated as complete genomes and are 3182-3221 bp.
- Ambiguous bases are below 1% for every record (only MH724252.1 has 3 Ns).
- Accessions are unique.
- Each sequence was rotated to the NC_003977.2 origin by a unique 25-mer vote;
  the offset, orientation and k-mer support are in `hbv_metadata.tsv`.

## Files

- `hbv_reference.fasta` - mapping reference (NC_003977.2).
- `hbv_public_genomes.fasta` - 10 public genomes, origin-normalised.
- `hbv_public_genomes.raw.fasta` - the same records before rotation.
- `hbv_metadata.tsv` - accession, genotype, country, date, length and QC fields.
- `genbank/` - cached GenBank flat files.
- `fetch_manifest.json` - retrieval URL, accessions and SHA-256 checksums.
