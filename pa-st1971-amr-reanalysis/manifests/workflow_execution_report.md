# Workflow execution report

Generated: 2026-11-18T18:14:59Z

## Dataset

- Isolate: *Pseudomonas aeruginosa* strain 71 (ST1971)
- Genome: `CP196749.1` / `NZ_CP196749.1`, 6,589,538 bp
- BioProject: PRJNA1285411
- Raw reads: not public; the finished chromosome is the input

## Execution

- Host CPUs: 8
- Annotation: GenBank flat file (authors' deposited annotation)
- AMRFinderPlus database: 2025-07-16.1
- CARD database: 4.0.2
- Commands: `bash bin/00_stage_databases.sh` then `bash bin/run_all.sh`

## Validation

| Check | Observed | Status |
|---|---|---|
| Genome length | 6589538 bp | PASS |
| Sequence type | ST1971 | PASS |
| Named ARGs | blaPDC-142, blaPME-1, blaOXA-395 | PASS |
| tmexCD2-toprJ2 | tmexC, tmexD2, toprJ | PASS |
| AMR symbols (non-point) | 19 | INFO |
| CARD unique ARO names | 62 | INFO |
| VFDB unique genes | 265 | INFO |

## Committed outputs

- `results/summary.md` and `results/summary.tsv`
- `results/amrfinder/`, `results/rgi/`, `results/virulence/`
- `results/figures/amr_gene_map.png` and `amr_classes.png`
- `manifests/amr_genes.tsv`, `rgi_calls.tsv`, `vfdb_genes.tsv`
- `manifests/paper_comparison.tsv`

## Caveats

- The paper's exact Bakta annotation was not rerun by default. The
  deposited GenBank proteins are used instead; optional Bakta mode is
  documented in the README.
- The public CARD and VFDB releases are newer than the paper's.
- A name in `point_mutations.tsv` can be a wildtype row. Compare the
  `Element name` and `Method` columns before calling a mutation present.
