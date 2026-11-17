# Committed summary manifests

These files are small, human-readable snapshots from the committed HBV run.
Full outputs live in `results/` locally and can be regenerated with the
workflow; `results/` is git-ignored by the repository convention.

- `software_versions.tsv` — tools and versions from both pixi environments.
- `reproducibility_manifest.json` — commands, inputs/outputs, SHA-256 checksums,
  validation checks and reference accessions.
- `workflow_execution_report.md` — run summary and validation checklist.
- `reference_accessions.txt` — the ten public GenBank accessions.
- `mapping_stats.tsv` — per-sample BWA mapping and circular coverage metrics.
- `consensus_stats.tsv` — consensus length, ambiguous bases and coverage status.
- `alignment_stats.txt` — MAFFT alignment summary.
- `closest_references.tsv` — genotype-matched comparison reference per sample.
- `mutation_summary.tsv` — variant counts by sample/region/effect.
- `phipack.txt` — full PhiPack recombination screen output.
