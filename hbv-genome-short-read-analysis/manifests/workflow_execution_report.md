# Workflow execution report

Generated: 2026-11-17T12:18:29.599363+00:00

## Dataset

- Five Illumina paired-end runs from PRJNA659786 (Brazil; three genotype A, two genotype D).
- 10 public complete HBV genomes from GenBank (A, B, C, D, E, F).
- Raw FASTQ files were downloaded from OmicsLab storage and checked against ENA MD5 values.
- Mapping reference: NC_003977.2 (genotype D, strain ayw, 3,182 bp).

## Execution

The nf-core/viralrecon 2.6.0 run used the `viralrecon` pixi environment (Nextflow 24.10.6; fastp 1.0.1, Bowtie2 2.5.4,
SAMtools 1.21, BCFtools 1.22). The downstream circular/consensus, alignment, phylogeny and annotation steps used the
default pixi environment (Nextflow 26.10.6, BWA 0.7.19, SAMtools 1.25, BCFtools 1.25, MAFFT 7.526, IQ-TREE 2.4.0).

The exact commands are stored in `reproducibility_manifest.json`; software versions are in `software_versions.tsv`.

## Validation

- Study samples: 5
- Public references: 10
- Tree taxa: 15 (all expected taxa present: True)
- Bootstrap support labels in tree: 12
- Consensus rows: 5
- Partial genomes (>5% N): HBV_A_B575_2014, HBV_D_B364_2014
- Figures generated: True
- CDS translations match GenBank annotation: True ({'P': True, 'S': True, 'X': True, 'C': True})

## Key observations

- The three genotype A samples form a clade with the Brazilian genotype A2 reference (100/100 UFBoot/SH-aLRT).
- The two genotype D samples fall in the genotype D clade with the RefSeq and Brazilian D references.
- Genotype B, C, E and F references provide outgroup context; the B/C clade is well supported.
- B575/2014 and B364/2014 have large low-coverage blocks (63.8% and 83.2% breadth at ≥10×) and are reported as partial genomes.
- PhiPack detects significant recombination signal; region-specific S and P trees are provided. Missing data may inflate the signal,
  so no recombination breakpoint is claimed.
- No clinical interpretation is made.

## Outputs

See `analysis_summary.html` for the integrated report, `variants/mutation_summary.html` for the variant page,
and `figures/` for publication-style figures.
