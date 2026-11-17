# Committed summary manifests

These files are small, human-readable snapshots from the committed HBV run.
The reference outputs live in `results/` (committed for this run; the larger BAM
files are omitted) and can be regenerated with the workflow.

## Run and environment

- `software_versions.tsv` — local pixi tools plus the versions reported by the
  platform `nf-core/viralrecon` run.
- `reproducibility_manifest.json` — commands, inputs/outputs, SHA-256 checksums,
  validation checks and reference accessions.
- `workflow_execution_report.md` — run summary and validation checklist.
- `reference_accessions.txt` — the ten public GenBank accessions.
- `viralrecon.hbv.omxa.json` — static platform analysis-job manifest for
  nf-core/viralrecon. `kraken2_db` is set to `/dev/null` because the platform
  SDK localises every `s3://` parameter before Nextflow starts, while nf-schema
  still validates the unused default path when `skip_kraken2` is true. The
  placeholder satisfies validation without staging the 8 GB default database.

## Mapping and consensus

- `mapping_stats.tsv` — per-sample BWA validation mapping. The `bwa_*` depth and
  breadth columns come from this independent BWA run, not from the platform
  Bowtie2 run. The `bowtie2_overall_alignment_rate` column is the platform
  value; `consensus_n_*` is read from the committed consensus FASTA.
- `consensus_stats.tsv` — consensus length and ambiguous bases, with mean depth
  and breadth computed from the platform BAM (`viralrecon_bowtie2_samtools_depth`).
  The `used_viralrecon_patched_N` suffix records N positions patched at the
  circular origin.

## Alignment

- `alignment_stats.txt` — human-readable MAFFT summary.
- `alignment_stats.tsv` — the same summary as metric/value rows.
- `per_sequence_stats.tsv` — gaps and `N` bases per sequence.
- `variable_sites.tsv` — one row per variable alignment column.

These files describe `results/downstream/hbv_alignment.fasta`: 15 sequences,
3,221 columns, 845 variable sites, 535 parsimony-informative sites and 39
gap-rich columns. No columns were trimmed.

## Variants and recombination

- `closest_references.tsv` — closest curated public genome for each study
  consensus, by global nucleotide identity.
- `nucleotide_variants.tsv` — one row per sample × substitution × annotated
  region. A position that falls in two overlapping ORFs appears twice.
- `amino_acid_variants.tsv` — one row per sample × region × amino-acid change.
- `mutation_summary.tsv` — the same substitutions aggregated by region and
  amino-acid effect. Overlapping ORFs are annotated independently, so the counts
  do not sum to the number of unique nucleotide changes.
- `indel_candidates.tsv` — six deletion candidates from a sample-vs-closest
  global alignment. Positions are approximate and the deletions are **not**
  applied to the reference-length consensus.
- `variant_calling_parameters.txt` — coordinate system, comparison reference and
  effect definitions used for the tables above.
- `phipack.txt` — full PhiPack output. It was generated from the earlier
  15-sequence alignment (533 informative sites), not the current 535-site
  alignment; see `recombination_screen.md` before reusing the p-values.
- `recombination_screen.md` — what the PhiPack tests do and do not support.
