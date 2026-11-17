# Workflow execution report

Revised: 2026-11-18. The original report was generated on 2026-11-17 from the
earlier local run; the summary below describes the committed platform reference
run and the downstream files that are actually present in this repository.

## Dataset

- Five Illumina paired-end runs from PRJNA659786 (Brazil; three genotype A, two
  genotype D).
- Ten complete public HBV genomes from GenBank (A, B, C, D, E, F).
- Mapping reference: NC_003977.2 (genotype D, strain ayw, 3,182 bp).

## Execution

The upstream `nf-core/viralrecon` step ran as an OmicsLab analysis job
(`75c29039-842d-49cf-b025-19566e03f976`) on 8 CPU / 16 GB public GreenNode
compute. The pipeline was `nf-core/viralrecon` `dev` commit
`31b9515f6e166542ca60358931351aa0f9a72b8a` (`v3.1.0dev-g31b9515`) on Nextflow
26.04.6; the run took 12m 21s. The job parameters are in
`results/viralrecon/pipeline_info/params_2026-11-17_20-37-11.json` and the
software versions are in
`results/viralrecon/pipeline_info/nf_core_viralrecon_software_mqc_versions.yml`.

The downstream steps used MAFFT 7.526, IQ-TREE 2.4.0 and Python 3.13 with
Biopython 1.88. The exact commands are in the root README and in
`reproducibility_manifest.json`.

## Validation

- Study samples: 5
- Public references: 10
- Tree taxa: 15 (all expected taxa present)
- Internal support labels in the tree: 12
- Consensus rows: 5
- Partial genomes (>5% `N`): HBV_A_B575_2014, HBV_D_B364_2014
- Figures committed: 4 (`genome_coverage`, `mutation_summary`,
  `phylogenetic_tree`, `qc_summary`)
- CDS translations match the GenBank annotation after removing the terminal
  stop: P, S, X and C all true

## Alignment

`results/downstream/hbv_alignment.fasta` has 15 sequences and 3,221 columns:

- 845 variable sites
- 535 parsimony-informative sites
- 310 singleton sites
- 0.73% gaps
- 3.48% `N` bases, almost all from the two partial genomes
- 39 gap-rich columns (>50% gaps) in two blocks, 2,356–2,361 and 2,863–2,895
- no columns were removed or trimmed

The 39 gap-rich columns form two blocks. The 2,356–2,361 block is a 6 bp
insertion in KJ854710.1 relative to every other sequence. The 2,863–2,895 block
is a 33 bp deletion in the A/D/RefSeq sequences relative to KJ and most B/C/E/F
references; the E sequence also has a gap at three positions in this block. The
first block overlaps the end of the B575/2014 low-coverage block; the second does
not. No columns were trimmed, so the alignment around these blocks should be
treated as uncertain.

## Key observations

- The three genotype A samples form a clade with the Brazilian A2 reference
  KJ854710.1 (100/100 UFBoot/SH-aLRT). Within that clade, B215 and B575 pair and
  B3392 branches next.
- The two genotype D samples fall in the D clade with NC_003977.2 and the
  Brazilian D references. The D pair has only 28.5/61 support, consistent with
  the missing block in B364/2014 and the small number of variable sites.
- The B and C references form a well-supported B/C grouping (97.4/92), with B
  and C each monophyletic (100/100). E and F provide outgroup context.
- B575/2014 and B364/2014 have large low-coverage blocks (65.1% and 83.1%
  breadth at ≥10×) and are reported as partial genomes.
- The bcftools VCFs contain 1,942 unique SNP positions across the five samples
  (660, 571, 481, 123 and 107 per sample); they contain SNP records only, with
  no indel records.
- An independent comparison with the closest curated genome gives 633
  region-annotated nucleotide rows and 593 amino-acid rows across the five
  samples, plus six deletion candidates. The nucleotide rows cover 473 unique
  sample–position pairs; overlapping ORFs are annotated independently, so the
  row count is larger than the number of unique positions. The full tables are
  `manifests/nucleotide_variants.tsv` and `manifests/amino_acid_variants.tsv`;
  `manifests/mutation_summary.tsv` is the aggregated view.
- The PhiPack screen in `phipack.txt` was run on the earlier alignment (533
  informative sites). PHI and NSS are below the 1,000-permutation resolution;
  Max χ² is p = 0.028. The panel spans genotypes A–F and includes partial
  genomes, so this is not a recombination breakpoint claim. See
  `recombination_screen.md`.

No clinical interpretation is made. No variant is labelled drug resistant or
immune escape.

## Outputs

| Path | Content |
|---|---|
| `results/viralrecon/` | platform viralrecon outputs (consensus, VCFs, QC, MultiQC) |
| `results/downstream/hbv_alignment.fasta` | MAFFT alignment of 5 study + 10 public genomes |
| `results/downstream/hbv_phylogeny.treefile` | IQ-TREE maximum-likelihood tree |
| `results/downstream/sample_summary.tsv` | mapping, depth, breadth and consensus `N` per sample |
| `results/downstream/variant_summary.tsv` | VCF SNPs by coding region and SNP/indel class |
| `results/downstream/coverage/*.depth.tsv` | per-base depth for the five samples |
| `results/figures/` | QC, coverage, mutation and phylogeny figures |
| `manifests/` | summary tables, annotation tables and this report |
