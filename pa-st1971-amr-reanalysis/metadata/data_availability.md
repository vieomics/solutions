# Read and assembly availability

Checked **2026-11-18**.

## What the paper deposited

| Item | Accession |
|---|---|
| Complete chromosome | `CP196749.1` (RefSeq `NZ_CP196749.1`) |
| BioProject | `PRJNA1285411` |
| BioSample | `SAMN49764163` |
| Organism | *Pseudomonas aeruginosa* strain 71 |

The paper sequenced the isolate with Illumina NovaSeq and Oxford Nanopore
MinION, then built a hybrid assembly. The data-availability statement deposits
the finished chromosome, not the raw reads.

## Read-run query

The ENA Portal API returns a header and **no rows** for this BioProject:

```bash
curl -fsSL 'https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJNA1285411&result=read_run&fields=run_accession,experiment_accession,sample_accession,fastq_ftp,read_count&format=tsv'
```

Observed output on 2026-11-18:

```text
run_accession	experiment_accession	sample_accession	fastq_ftp	read_count
```

The matching SRA query also returns zero runs:

```bash
curl -fsSL 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=sra&term=PRJNA1285411&retmode=json'
```

Observed on 2026-11-18: `"count":"0"`.

There are therefore no public FASTQ files to download, and a read-level or
hybrid-assembly reproduction is not possible from public data.

## Consequence for this solution

The finished chromosome is the only public single-sample input that reproduces
the paper's AMR result. AMRFinderPlus, CARD-RGI, MLST and VFDB all work on
nucleotide or protein sequences, so the resistome, sequence type and virulence
screens are unaffected by starting from the assembly.

If the authors deposit the reads later, run the same AMR steps on a new
assembly; the analysis scripts do not need to change.
