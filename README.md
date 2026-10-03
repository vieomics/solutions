# vieomics/solutions — NDM truncation investigation

Reproducible reanalysis of the five bacterial isolates with a discordant `blaNDM`
PCR / ceftazidime-avibactam phenotype reported by Dung et al. 2025
(*Ann Clin Microbiol Antimicrob*, doi:10.1186/s12941-025-00818-3).

- Raw data: ENA project [PRJEB86571](https://www.ebi.ac.uk/ena/browser/view/PRJEB86571)
- Branch: `topic/ndm-truncation`

| Run | Isolate | Reported species |
|-----|---------|------------------|
| ERR14693661 | 03-A-063 | *Klebsiella pneumoniae* |
| ERR14693662 | 03-A-038 | *Klebsiella pneumoniae* |
| ERR14693663 | 24-A-028 | *Klebsiella pneumoniae* |
| ERR14693664 | 11-A-427 | *Klebsiella pneumoniae* |
| ERR14693665 | 021-A-244 | *Pseudomonas aeruginosa* (ENA `scientific_name` field is mislabelled as *K. pneumoniae*) |

## Pipeline (quick check)

1. **Fetch** — `nf-core/fetchngs` 1.13.0 (download + MD5 verification)
2. **Assemble / annotate** — `nf-core/bacass` 2.6.1

```bash
nextflow run nf-core/fetchngs -r 1.13.0 -profile docker \
    --input ids.csv --outdir results/fetchngs -resume

python3 bin/fetchngs_to_bacass.py \
    --input results/fetchngs/samplesheet/samplesheet.csv \
    --output bacass_samplesheet.tsv

nextflow run nf-core/bacass -r 2.6.1 -profile docker \
    --input bacass_samplesheet.tsv --outdir results/bacass \
    --assembly_type short --assembler unicycler \
    --annotation_tool prokka --skip_kraken2 -resume
```

## Investigation notes

Read-level audit of the reported `blaNDM` truncations, distinguishing:

- **H1** true deletion
- **H2** assembly artifact (repeat collapse / coverage dropout)
- **H3** mobile remnant or second (silent) copy
- **H4** intact but silenced allele (promoter disruption)

Follow-up: public `blaNDM` junction recurrence and co-selection mining.

`results/` and `work/` are not tracked.
