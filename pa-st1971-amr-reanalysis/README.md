# Pseudomonas aeruginosa ST1971 AMR reanalysis (Nguyen et al. 2026)

Single-sample, command-line reproduction of the AMR part of:

> Nguyen QH, Nguyen TS, Tran TTT, et al. **Genomic characterization of an
> extensively drug-resistant high-risk *Pseudomonas aeruginosa* ST1971
> harbouring tmexCD2–toprJ2 from a Vietnamese patient with urinary tract
> infection.** *Journal of Global Antimicrobial Resistance* 48 (2026) 127–130.
> [doi:10.1016/j.jgar.2026.03.007](https://doi.org/10.1016/j.jgar.2026.03.007)

This is one self-contained solution in the
[vieomics/solutions](../README.md) repository.

## The question

Does the public genome of *P. aeruginosa* strain 71 reproduce the paper's
resistome: 18 acquired ARGs (including `blaPDC-142`, `blaPME-1`, `blaOXA-395`),
the colistin-associated point mutations, and the `tmexCD2–toprJ2` efflux
cluster?

## The data (one sample)

| Item | Value |
|---|---|
| Isolate | *P. aeruginosa* strain 71 |
| Genome | [CP196749.1](https://www.ncbi.nlm.nih.gov/nuccore/CP196749.1) / [NZ_CP196749.1](https://www.ncbi.nlm.nih.gov/nuccore/NZ_CP196749.1) |
| Size | 6,589,538 bp, one circular chromosome |
| BioProject | [PRJNA1285411](https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1285411) |
| BioSample | [SAMN49764163](https://www.ncbi.nlm.nih.gov/biosample/SAMN49764163) |
| Paper phenotype | XDR; imipenem 16, meropenem 32, colistin 32, levofloxacin >128, tigecycline 16 mg/L |

**Why start from the assembly?** The paper's data-availability statement
deposits only the finished chromosome. On 2026-11-13 the ENA/SRA read-run
query for PRJNA1285411 returned zero runs, so the raw Illumina/Nanopore reads
are not publicly available. The finished chromosome is therefore the
reproducible single-sample input. If reads are deposited later, the same
resistome steps can be run on a new assembly without changing the AMR tools.

## What the workflow does

```text
ENA FASTA
   │
   ├─ seqkit stats ................. length / GC / integrity checks
   ├─ Bakta 1.10.3 ................. gene annotation (light DB)
   ├─ mlst 2.35.0 ................. PubMLST Pseudomonas scheme → ST1971
   ├─ AMRFinderPlus 4.0.19 ........ ARGs + point mutations
   ├─ CARD-RGI 6.0.3 .............. second ARG caller
   └─ ABRicate + VFDB ............. virulence-factor context
          │
          └─ results/summary.md
```

Everything is installed by [pixi](https://pixi.sh). There is no Nextflow,
Docker, Apptainer, or conda activation step. The scripts are plain Bash.

## Status

| Step | Script | Status |
|---|---|---|
| 0. Check pixi environments | `bin/00_check_env.sh` | ✅ done |
| 1. Download genome | `bin/01_download_genome.sh` | ✅ done |
| 2. Genome QC | `bin/02_genome_qc.sh` | ✅ done |
| 3. Bakta annotation | `bin/03_annotate.sh` | ⏳ interrupted during first database download |
| 4. MLST | `bin/04_mlst.sh` | ⬜ pending |
| 5. AMRFinderPlus | `bin/05_amrfinder.sh` | ⬜ pending |
| 6. CARD-RGI | `bin/06_rgi_card.sh` | ⬜ pending |
| 7. VFDB | `bin/07_vfdb.sh` | ⬜ pending |
| 8. Summary | `bin/08_summarize.sh` | ⬜ pending |

The step-by-step tutorial, exact commands, manual download links and
troubleshooting notes live in **[`docs/tutorial.md`](docs/tutorial.md)**.

## Quick start

```bash
# One-time environment setup (installs all five pixi environments)
pixi install --all

# Check the tools
bash bin/00_check_env.sh

# Run everything
bash bin/run_all.sh
```

The first run downloads:

| Resource | Size | Where |
|---|---|---|
| *P. aeruginosa* chromosome | 6.4 MB | `data/CP196749.1.fasta` |
| Bakta light database | ~1.5 GB | `db/bakta-light/` |
| AMRFinderPlus database | ~200 MB | `db/amrfinder/` |
| CARD database | ~4 MB compressed | `db/card/` |

All generated data, databases, results and pixi environments are git-ignored.

## Why the Bakta *light* database?

Bakta 1.10.3's **full** database is 39.4 GB to download. The **light**
database is ~1.5 GB and gives the standard Bakta gene annotation. The AMR
calls in this solution come from AMRFinderPlus and CARD-RGI, and the sequence
type comes from `mlst`, so the light database is enough. Set
`BAKTA_DB_TYPE=full` if you deliberately want Bakta's extra cross-references.

## What is reproduced, and what is simplified

| Paper analysis | Here | Note |
|---|---|---|
| Complete genome, 6,589,538 bp | ✅ `seqkit` | exact public assembly |
| ST1971 | ✅ `mlst` | same PubMLST scheme |
| Bakta v1.10.3 annotation | ✅ same version | light DB by default |
| AMRFinderPlus v4.0.19 ARGs + `mutation_all` | ✅ same version | core result |
| CARD-RGI v6.0.3 | ✅ same version | current CARD data |
| VFDB virulence factors | ✅ ABRicate + VFDB | paper used the VFinder web service |
| MobileElementFinder, PHASTER, ANI/SNP comparisons | ❌ not included | web-only or multi-genome analyses, outside this single-sample AMR scope |
| Illumina + Nanopore hybrid assembly | ❌ not possible | raw reads are not public |

The aim is to keep the paper's AMR result quality while replacing the
multi-tool stack with one readable Bash pipeline.

## Layout

```text
pa-st1971-amr-reanalysis/
├── README.md
├── pixi.toml / pixi.lock      # five small pinned environments
├── bin/
│   ├── 00_check_env.sh
│   ├── 01_download_genome.sh
│   ├── 02_genome_qc.sh
│   ├── 03_annotate.sh
│   ├── 04_mlst.sh
│   ├── 05_amrfinder.sh
│   ├── 06_rgi_card.sh
│   ├── 07_vfdb.sh
│   ├── 08_summarize.sh
│   └── run_all.sh
├── docs/tutorial.md           # progress tracker + beginner walkthrough
├── data/                      # downloaded FASTA (ignored)
├── db/                        # tool databases (ignored)
├── results/                   # outputs (ignored)
└── logs/                      # run logs (ignored)
```
