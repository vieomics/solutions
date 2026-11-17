# Reference results

Successful end-to-end `nf-core/viralrecon` run used as the reference material
for the solution.

| Item | Value |
|---|---|
| Job | `75c29039-842d-49cf-b025-19566e03f976` |
| Workspace | Vieomics (`c29526fd-a388-41e8-a452-141e8bbcece0`) |
| Compute | GreenNode-HCM, 8 CPU / 16 GB |
| Pipeline | `nf-core/viralrecon` `dev`, commit `31b9515f6e166542ca60358931351aa0f9a72b8a` |
| Inputs | public Omicslab workspace, `s3://omicslab/data/analysis/PRJNA659786/` |
| Outputs | `s3://vieomics-prod/data/viralrecon/hbv/results` |
| Created | 2026-11-18 03:33 (Asia/Ho_Chi_Minh) |
| Finished | 2026-11-18 03:48 (Asia/Ho_Chi_Minh) |
| Runtime | 12m 21s |

## Parameters

```text
platform              illumina
protocol              metagenomic
genome                hbv
variant_caller        bcftools
consensus_caller      bcftools
skip_assembly         true
skip_kraken2          true
skip_fastqc           true
skip_freyja           true
skip_freyja_boot      true
skip_pangolin         true
skip_nextclade        true
skip_snpeff           true
skip_variants_quast   true
skip_variants_long_table true
skip_picard_metrics   true
skip_mosdepth         true
skip_consensus_plots  true
kraken2_db            /dev/null
```

## Viralrecon results

| Path | Content |
|---|---|
| `viralrecon/variants/bcftools/consensus/bcftools/*.consensus.fa` | five consensus genomes |
| `viralrecon/variants/bcftools/*.vcf.gz` | final and normalised variant calls |
| `viralrecon/variants/bcftools/bcftools_stats/` | BCFtools variant statistics |
| `viralrecon/variants/bowtie2/samtools_stats/` | mapping statistics |
| `viralrecon/variants/bowtie2/log/` | Bowtie2 alignment logs |
| `viralrecon/fastp/` | read trimming reports |
| `viralrecon/multiqc/multiqc_report.html` | combined QC report |
| `viralrecon/pipeline_info/` | Nextflow execution report, timeline, trace, DAG and parameters |
| `figures/` | QC, genome coverage, mutation summary and phylogeny figures |

`skip_mosdepth` is `true` in the platform run. The mean depth and breadth values
in `downstream/sample_summary.tsv` were therefore computed with `samtools depth`
on the viralrecon BAM, not by mosdepth. They are the coverage numbers used in
the root README table.

The consensus is a **reference-guided base consensus**, not a de novo assembly.
It keeps the 3,182 bp NC_003977.2 coordinate frame; indels are not applied.
Positions below 10× (or with no covering read) are written as `N`. In the three
genotype A samples this leaves a short `N` run at 2,856–2,872; B575/2014 and
B364/2014 have much larger low-coverage blocks. The six deletion candidates
relative to the closest public genome are listed in
`manifests/indel_candidates.tsv` and are not represented as gaps in these
consensus sequences.

## Downstream analysis

| Path | Content |
|---|---|
| `downstream/all_hbv_sequences.fasta` | five consensus genomes + ten public genomes |
| `downstream/all_hbv_metadata.tsv` | genotype, country, date and sample/reference labels |
| `downstream/hbv_alignment.fasta` | MAFFT alignment (15 sequences) |
| `downstream/hbv_phylogeny.treefile` | IQ-TREE maximum-likelihood tree |
| `downstream/hbv_phylogeny.iqtree` | model and support values |
| `downstream/coverage/*.depth.tsv` | per-base depth for the five samples |
| `downstream/sample_summary.tsv` | mapping rate, mean depth, breadth, consensus N |
| `downstream/variant_summary.tsv` | VCF SNPs by coding region and SNP/indel class |

`downstream/variant_summary.tsv` counts each VCF record once per overlapping
open reading frame, so the S/P/C/X columns overlap and are larger than the
1,942 unique SNP positions. The VCFs are relative to the mapping reference
NC_003977.2. The separate `manifests/mutation_summary.tsv` is relative to the
closest curated genome for each sample and should not be compared directly with
the VCF counts.

The five BAM files are omitted from the repository. They remain in the
workspace output prefix above. The four figures in `figures/` were generated
from these results; the phylogeny figure is reproduced by the code block in the
root README.
