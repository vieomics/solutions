# Public-genome ARG heatmap reference run

Fig. 1B-style ARG heatmap for the ST1971 genomes that are public as
**assemblies**. The paper compared strain 71 with 24 public genomes; twelve of
those are raw-read-only (`SRR...`) and need assembly, so this reference run
uses the **13 genomes available as GCA assemblies**, including strain 71.

| Item | Value |
|---|---|
| Run date | 2026-11-18 |
| Genomes | 13 (strain 71 + 12 public GCA assemblies) |
| ARG columns | 40 acquired genes |
| Matrix entries | 220 ARG copies (capped at 3 per gene/genome) |
| Tool | AMRFinderPlus 4.0.19 |
| Database | 2025-07-16.1 |
| Mode | nucleotide, acquired `AMR` rows only; point calls excluded |
| Figure | `arg_heatmap.png` |

## Genomes

`genomes.tsv` is the authoritative list: accession, label, country, assembly
directory, local gzip path and MD5. The study sample is `GCA_051905005`
(Vietnam); the other twelve are from Greece and China.

The following paper rows are **not** in this heatmap because they are deposited
only as raw reads:

```text
SRR19860581  SRR19860580  SRR18959489  SRR19860452
SRR18959485  SRR18959490  SRR19860462  SRR19859522
SRR19860415  SRR18959434  SRR18959386  SRR18959387
```

## Outputs

| File | Content |
|---|---|
| `arg_heatmap.png` | Fig. 1B-style heatmap (13 genomes × 40 ARGs) |
| `arg_matrix.tsv` | genome × ARG copy-number matrix |
| `arg_hits_long.tsv` | one row per genome × gene hit |
| `summary.tsv` | genome/gene counts and study-sample total |
| `genomes.tsv` | accession, country, assembly directory and MD5 |
| `amrfinder/*.tsv` | raw AMRFinderPlus output per genome |

## Observations from the 13-genome matrix

- The study sample has 21 ARG copies in the matrix; the 13 genomes range from
  12 to 28.
- Strain 71 carries the expected `blaPDC-142`, `blaPME-1`, `blaOXA-395` and
  `tmexC`/`tmexD2`/`toprJ` columns.
- The Greek genome `GCA_043498125` has the largest ARG copy count (28) and is
  the most distinct row in this small panel.
- Several Chinese genomes share the same ARG profile, so the row dendrogram
  mostly reflects presence/absence blocks, not a fine-grained phylogeny.

## Caveats

- This is **13 of 25** paper genomes; do not present it as the complete Fig. 1B.
- The 12 missing genomes need read QC and assembly from their `SRR` runs.
- The AMRFinderPlus database is newer than the authors' snapshot.
- Several GCA assemblies are drafts with multiple contigs; a gene split
  across contigs can be missed or counted differently.
- The dendrogram is average-linkage clustering of ARG copy profiles. It is not
  an ANI tree and should not be used for phylogenetic claims.

## Regenerate

```bash
bash analysis/arg_heatmap/fetch_genomes.sh
pixi run -e annotation bash analysis/arg_heatmap/run_amrfinder.sh
pixi run -e viz python analysis/arg_heatmap/plot_heatmap.py
```
