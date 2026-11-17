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
| `downstream/variant_summary.tsv` | variants by coding region and SNP/indel class |

The five BAM files (234 MB) are omitted from the repository. They remain in the
workspace output prefix above. The figures in `figures/` were generated from
these results; the tree figure is reproduced by the code block in the root
README.
