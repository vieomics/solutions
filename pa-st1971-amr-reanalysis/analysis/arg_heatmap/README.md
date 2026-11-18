# Public-genome ARG heatmap (13 of 25)

A Fig. 1B-style ARG presence/copy-number heatmap for the ST1971 genomes that
are public as **assemblies**. The paper compared strain 71 with 24 public
ST1971 genomes. Twelve of those are deposited only as raw reads (`SRR...`), so
they need assembly before they can join the heatmap. The remaining twelve,
plus strain 71 itself, are available as `GCA` assemblies — 13 genomes total.

## Genomes included

| Accession | Label | Country |
|---|---|---|
| `GCA_051905005` | strain 71 (this study) | Vietnam |
| `GCA_043498125` | public assembly | Greece |
| `GCA_035818655` | public assembly | China |
| `GCA_011683115` | public assembly | China |
| `GCA_011683045` | public assembly | China |
| `GCA_001721845` | public assembly | China |
| `GCA_001722045` | public assembly | China |
| `GCA_001721745` | public assembly | China |
| `GCA_001721805` | public assembly | China |
| `GCA_001721765` | public assembly | China |
| `GCA_001722025` | public assembly | China |
| `GCA_001721825` | public assembly | China |
| `GCA_001721785` | public assembly | China |

## Genomes still missing

These 12 paper rows are raw-read runs only and need assembly before they can be
added:

```text
SRR19860581  SRR19860580  SRR18959489  SRR19860452
SRR18959485  SRR18959490  SRR19860462  SRR19859522
SRR19860415  SRR18959434  SRR18959386  SRR18959387
```

The fetch script and heatmap script are written as a manifest loop, so adding
these later only requires an assembly FASTA and a row in
`results/heatmap/genomes.tsv`.

## Run

```bash
# 1. Fetch the 13 GCA assemblies from NCBI (once)
bash analysis/arg_heatmap/fetch_genomes.sh

# 2. Run AMRFinderPlus on each assembly
pixi run -e annotation bash analysis/arg_heatmap/run_amrfinder.sh

# 3. Build the matrix and the figure
pixi run -e viz python analysis/arg_heatmap/plot_heatmap.py
```

## Method

- AMRFinderPlus 4.0.19 with the staged database `2025-07-16.1`.
- Nucleotide mode, because the public assemblies do not all ship an annotation.
- Only `Type = AMR` rows are counted; point-mutation calls (`Method = POINT*`)
  are excluded because the paper's Fig. 1B is an acquired-ARG heatmap.
- Values are the number of AMRFinderPlus hits for that gene in that genome,
  capped at 3 for the colour scale.
- Columns are grouped by antibiotic class and then gene name.
- Rows are clustered by ARG copy-number profile with average linkage. With 13
  nearly clonal genomes this is a presentation aid, not a population tree.

## Outputs

| File | Content |
|---|---|
| `results/heatmap/arg_heatmap.png` | Fig. 1B-style heatmap for 13 genomes |
| `results/heatmap/arg_matrix.tsv` | genome × ARG copy-number matrix |
| `results/heatmap/arg_hits_long.tsv` | one row per genome × gene hit |
| `results/heatmap/summary.tsv` | genome/gene counts and study-sample total |
| `results/heatmap/genomes.tsv` | accession, label, country and source checksum |
| `results/heatmap/amrfinder/*.tsv` | raw AMRFinderPlus output per genome |

## Caveats

- This is **13 of 25** genomes. It is not the paper's complete Fig. 1B.
- The AMRFinderPlus database is newer than the one available to the authors,
  so the gene panel and copy counts can differ at the margins.
- Several of the GCA assemblies are draft genomes with multiple contigs; a gene
  split across contigs may be missed or counted differently.
- The dendrogram groups similar ARG profiles; it is not an ANI tree and should
  not be used as a phylogenetic claim.
