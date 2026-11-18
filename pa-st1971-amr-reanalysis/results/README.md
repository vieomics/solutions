# Reference results

Single-sample reference run committed with this solution. The analysis is
small enough to keep in git, so a reader can inspect the real output without
downloading databases or rerunning the tools.

| Item | Value |
|---|---|
| Run date | 2026-11-18 |
| Isolate | *Pseudomonas aeruginosa* strain 71 (ST1971) |
| Input | `CP196749.1`, 6,589,538 bp |
| Genome MD5 | `0a70bcde2b23a14b74033a6da8078b24` |
| Genome SHA-256 | `fc3b0d965bd6e7e752b87a2211ab6c85c24f40905c15672e377136adaab97041` |
| Annotation | deposited GenBank annotation, 6,012 translated CDS |
| AMRFinderPlus | 4.0.19, database 2025-07-16.1 |
| CARD-RGI | 6.0.3, CARD 4.0.2 |
| mlst | 2.35.0, PubMLST `paeruginosa` |
| ABRicate/VFDB | 1.4.0, VFDB release 2026-Nov-18 |
| Host | 8 CPU container, 16 threads requested |

## What the run found

| Check | Observed |
|---|---|
| Genome size | 6,589,538 bp |
| GC | 66.17% |
| Sequence type | ST1971 (perfect allele match) |
| AMRFinderPlus AMR symbols | 23 including point calls; 19 non-point |
| Named ARGs | `blaPDC-142`, `blaPME-1`, `blaOXA-395` |
| Tigecycline cluster | `tmexC`, `tmexD2`, `toprJ` |
| Non-wildtype colistin call | `pmrB_V15I` |
| CARD unique ARO names | 62 (includes intrinsic efflux pumps) |
| VFDB | 284 hits, 265 unique genes |

The paper reports 18 acquired ARGs and 213 virulence factors. The AMR count is
close but not identical because counting conventions differ (partial genes and
the three `tmexCD2–toprJ2` subunits). The VFDB number is higher because the
committed run uses a newer VFDB release and ABRicate counts hits, not the
paper's VFinder workflow. See `manifests/paper_comparison.tsv`.

## Committed outputs

| Path | Content |
|---|---|
| `qc/` | seqkit statistics and the genome length/gap checks |
| `mlst/` | PubMLST profile and the ST1971 check |
| `annotation/` | protein FASTA, GFF3 and annotation source summary |
| `amrfinder/` | core AMR table, plus-gene table, point mutations and versions |
| `rgi/` | CARD-RGI calls, JSON and version |
| `virulence/` | VFDB hits and ABRicate version |
| `figures/` | AMR gene map and antibiotic-class bar chart |
| `summary.md` | human-readable summary of the whole run |
| `summary.tsv` | one metric per row, easy to diff between runs |

The databases (`db/`), downloaded inputs (`data/`), pixi environments
(`.pixi/`) and run logs (`logs/`) are not committed. The AMRFinderPlus and
CARD databases can be staged again with `bin/00_stage_databases.sh`.

## Multi-genome add-on

`results/heatmap/` is a separate Fig. 1B-style ARG heatmap for the 13 ST1971
genomes that are public as GCA assemblies (strain 71 + 12 public genomes). The
other 12 paper genomes are raw-read-only and are not included yet. See
`results/heatmap/README.md` and `analysis/arg_heatmap/` for the script and
provenance.

## Annotation note

The committed run uses the **authors' deposited GenBank annotation**, extracted
by `bin/03_prepare_annotation.py`, rather than rerunning Bakta. This keeps the
quick start free of a 1.5 GB database download. The paper used Bakta 1.10.3;
`ANNOTATION_SOURCE=bakta bash bin/03_annotate.sh` reproduces that annotation if
the light database is available. AMRFinderPlus and CARD-RGI are run on the same
kind of protein/GFF input either way.

## Rebuild

```bash
pixi install --all
bash bin/00_stage_databases.sh   # optional prefetch; run_all also calls it
bash bin/run_all.sh
```

`run_all.sh` is safe to rerun: existing downloads and databases are reused.
