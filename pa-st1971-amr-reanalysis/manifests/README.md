# Committed summary manifests

Small, human-readable snapshots from the committed PA-ST1971 run. The raw tool
outputs stay in `results/`; these tables make the comparison easy to inspect
and diff.

## Run and environment

- `software_versions.tsv` — pixi and tool versions, with the environment that
  provides each tool.
- `database_versions.tsv` — AMRFinderPlus and CARD versions, and where they
  were staged from.
- `reproducibility_manifest.json` — input checksums, annotation source,
  database versions, commands and SHA-256 checksums of the main result files.
- `workflow_execution_report.md` — run summary and validation checklist.

## Resistome

- `amr_genes.tsv` — unique AMRFinderPlus AMR symbols with class, subclass,
  method and chromosome coordinates. Point calls are included; filter on the
  `method` column to exclude them.
- `point_mutations.tsv` — the full AMRFinderPlus `mutation_all` table. A row can
  be a **wildtype** variant that was considered but not called. Check the
  `Element name` (`[WILDTYPE]`) and `Method` columns before reporting a
  mutation as present.
- `rgi_calls.tsv` — unique CARD-RGI best hits with cut-off, identity, drug
  class, resistance mechanism and AMR gene family. RGI reports intrinsic
  efflux pumps as well as acquired genes.
- `vfdb_genes.tsv` — unique VFDB genes with product, database, hit count and
  best identity.
- `vfdb_categories.tsv` — the paper's VF category counts (effector delivery,
  mobility, biofilm, adherence, etc.) next to the committed VFDB snapshot.
- `paper_comparison.tsv` — the paper's headline numbers next to the observed
  values, plus a `scope` block listing the analyses that are not reproduced
  (AST/MIC, hybrid assembly, MGEs, prophages, CRISPR, islands, ANI/SNP,
  GeneViewer/Proksee, the 12 raw-read-only heatmap genomes).

## Interpreting the comparison

The paper and this run use different database snapshots and slightly different
counting conventions:

- **18 versus 19 non-point AMR symbols.** The observed count includes the
  partial `blaKBL` call and counts `tmexC`, `tmexD2` and `toprJ` as three
  symbols. Treat the paper's 18 as the benchmark, not as a target to force by
  changing thresholds.
- **213 versus 265 VFDB genes.** ABRicate 1.4.0 bundles a newer VFDB release
  and counts nucleotide hits. The paper used the VFinder web service.
- **Colistin mutations.** AMRFinderPlus calls only `pmrB_V15I` as non-wildtype
  in this run. The other variants named in the paper appear in
  `point_mutations.tsv` as wildtype/considered rows, which is a database and
  reference-coordinate difference, not proof that the genome lacks them.
- **CARD 62 ARO names.** This includes the intrinsic `Mex`/`Opr` efflux
  systems. It is not comparable to the paper's acquired-ARG count.
