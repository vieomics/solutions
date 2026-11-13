# Tutorial: single-sample AMR reanalysis with Bash + pixi

This is the beginner-friendly, manual version of the *P. aeruginosa* ST1971
analysis from Nguyen et al. (2026). It assumes you know how to open a terminal
and run `cd`, but not Nextflow, Docker, Apptainer or workflow managers.

The guiding rule: **one tool, one pixi environment, one Bash script, one plain
output file**. If something fails, you can see exactly which command failed.

---

## Progress tracker

Update the boxes as you work through the tutorial.

| # | Step | Command | Status |
|---|---|---|---|
| 0 | Read paper, find accession | — | ✅ CP196749.1 |
| 1 | Check public reads | ENA/SRA query | ✅ none deposited |
| 2 | Build pixi environments | `pixi install --all` | ✅ done |
| 3 | Download genome + MD5 | `bin/01_download_genome.sh` | ✅ done |
| 4 | Genome QC | `bin/02_genome_qc.sh` | ✅ done |
| 5 | Bakta annotation | `bin/03_annotate.sh` | ⏳ download interrupted; resume |
| 6 | MLST | `bin/04_mlst.sh` | ⬜ pending |
| 7 | AMRFinderPlus | `bin/05_amrfinder.sh` | ⬜ pending |
| 8 | CARD-RGI | `bin/06_rgi_card.sh` | ⬜ pending |
| 9 | VFDB / ABRicate | `bin/07_vfdb.sh` | ⬜ pending |
| 10 | Summary | `bin/08_summarize.sh` | ⬜ pending |

**Current stopping point:** the Bakta **light** database download reached
744 MB of ~1.5 GB and was interrupted. No analysis result is affected. Resume
with:

```bash
pixi run -e annotation bash bin/03_annotate.sh
```

`bakta_db download` will reuse/complete `db/bakta-light/db-light.tar.gz` or
download it again; either way it is safe to rerun.

---

## 0. What the paper deposited

| Item | Accession |
|---|---|
| Complete chromosome | `CP196749.1` (RefSeq `NZ_CP196749.1`) |
| BioProject | `PRJNA1285411` |
| BioSample | `SAMN49764163` |
| Isolate | *Pseudomonas aeruginosa* strain 71 |
| Genome size | 6,589,538 bp |
| Reported ST | ST1971 |

The paper performed Illumina + Nanopore sequencing and a Unicycler hybrid
assembly. It deposited the finished chromosome, but **not** the raw reads. A
read-run query for `PRJNA1285411` in ENA/SRA returns zero runs (checked
2026-11-13). That is why this tutorial starts from the assembly: it is the
only public single-sample data that reproduces the AMR result.

This is not a shortcut around the biology. AMRFinderPlus and CARD-RGI work on
nucleotide/protein sequences, so the resistome result is the same whether the
input came from a new assembly or the deposited one.

---

## 1. Install pixi (once)

```bash
curl -fsSL https://pixi.sh/install.sh | bash
export PATH="$HOME/.pixi/bin:$PATH"
pixi --version
```

`pixi` creates isolated environments from `pixi.toml` and records exact
package versions in `pixi.lock`. No `conda activate`, no containers.

Enter this solution and install all five environments:

```bash
cd solutions/pa-st1971-amr-reanalysis
pixi install --all
```

Why five environments? The paper pins old versions of Bakta and RGI. RGI
6.0.3 pins `biopython 1.78`, which conflicts with newer annotation packages.
Separate environments keep the pins exact and prevent "works on my machine"
solver surprises:

| Environment | Tools |
|---|---|
| default | seqkit, BLAST, curl, coreutils |
| annotation | Bakta 1.10.3, AMRFinderPlus 4.0.19 |
| typing | mlst 2.35.0 |
| resistome | CARD-RGI 6.0.3 |
| virulence | ABRicate 1.4.0 |

Check them:

```bash
bash bin/00_check_env.sh
```

Expected: `seqkit v2.14.0`, `bakta 1.10.3`, `4.0.19`, `mlst 2.35.0`,
`Resistance Gene Identifier - 6.0.3`, `abricate 1.4.0`.

---

## 2. Download the genome (raw commands)

The script is convenient, but here is exactly what it does, with no variables:

```bash
mkdir -p data
curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused \
  https://www.ebi.ac.uk/ena/browser/api/fasta/CP196749.1 \
  -o data/CP196749.1.fasta

echo "0a70bcde2b23a14b74033a6da8078b24  data/CP196749.1.fasta" | md5sum -c -
```

Expected last line:

```text
data/CP196749.1.fasta: OK
```

Then:

```bash
pixi run bash bin/01_download_genome.sh
```

The script also writes `data/download_info.txt` with the URL, accession,
MD5, SHA-256 and a note about the missing raw reads.

> **Why ENA and not NCBI?** The ENA browser API returns the FASTA directly
> without the E-utilities rate limit. The sequence is the same `CP196749.1`
> deposited by the authors.

---

## 3. Check the FASTA before annotating

```bash
pixi run bash bin/02_genome_qc.sh
```

It runs `seqkit stats -a -T` and asserts:

| Check | Expected | Observed |
|---|---|---|
| sequences | 1 | 1 |
| length | 6,589,538 bp | 6,589,538 bp |
| gaps | 0 | 0 |
| GC | ~66.17% | 66.17% |

Output: `results/qc/seqkit_stats.tsv` and `results/qc/genome_check.tsv`.

This step is not bureaucracy. It catches a truncated download or an HTML
error page before a long annotation run.

---

## 4. Annotate with Bakta 1.10.3

### 4a. Download the database

The paper used Bakta 1.10.3. Its **full** database is **39.4 GB** (checked
from the Zenodo record), which is unreasonable for a tutorial. The **light**
database is **1.48 GB** and contains the standard Bakta annotation models.
Because AMRFinderPlus, CARD-RGI and MLST are run separately below, the light
database does not reduce the AMR result quality.

Raw download command:

```bash
mkdir -p db/bakta-light
pixi run -e annotation bakta_db download \
  --output db/bakta-light \
  --type light
```

If `bakta_db` is slow or stalls, use the direct Zenodo file:

```bash
mkdir -p db/bakta-light
curl -fL --retry 5 --retry-delay 5 -C - \
  https://zenodo.org/records/10522951/files/db-light.tar.gz \
  -o db/bakta-light/db-light.tar.gz

# size: 1,483,565,256 bytes
# md5:  31b3fbdceace50930f8607f8d664d3f4
md5sum db/bakta-light/db-light.tar.gz

tar -xzf db/bakta-light/db-light.tar.gz \
  -C db/bakta-light --strip-components=1
```

`-C -` tells curl to resume a partial file. If the database directory already
has `version.json`, the script skips the download.

### 4b. Run Bakta

Raw command:

```bash
mkdir -p results/bakta
pixi run -e annotation bakta \
  --db db/bakta-light \
  --output results/bakta \
  --prefix strain71 \
  --threads 16 \
  --force \
  data/CP196749.1.fasta
```

Or:

```bash
pixi run -e annotation bash bin/03_annotate.sh
```

Useful outputs:

| File | What it is |
|---|---|
| `results/bakta/strain71.faa` | protein FASTA, needed by AMRFinderPlus |
| `results/bakta/strain71.ffn` | nucleotide CDS FASTA |
| `results/bakta/strain71.gff3` | annotation for genome browsers |
| `results/bakta/strain71.tsv` | one row per feature |
| `results/bakta/strain71.txt` | summary counts |

> **Optional full database:** `BAKTA_DB_TYPE=full pixi run -e annotation bash
> bin/03_annotate.sh`. Only do this with ~40 GB free and a fast connection.

---

## 5. Confirm the sequence type with mlst

Raw command:

```bash
mkdir -p results/mlst
pixi run -e typing mlst \
  --scheme paeruginosa \
  --full \
  --threads 16 \
  --nopath \
  data/CP196749.1.fasta \
  > results/mlst/mlst.tsv
```

Or:

```bash
pixi run -e typing bash bin/04_mlst.sh
```

Expected: scheme `paeruginosa`, ST `1971`. The script writes
`results/mlst/mlst_check.tsv` and warns if the ST differs.

> The scheme name is `paeruginosa`, not `pseudomonas`. Run
> `pixi run -e typing mlst --list` to see all scheme names.

---

## 6. Call ARGs and point mutations with AMRFinderPlus

The conda package does not ship the database. Download it once:

```bash
mkdir -p db/amrfinder
pixi run -e annotation amrfinder_update \
  --database db/amrfinder \
  --force_update
```

Raw analysis command:

```bash
mkdir -p results/amrfinder
pixi run -e annotation amrfinder \
  --nucleotide data/CP196749.1.fasta \
  --protein results/bakta/strain71.faa \
  --organism Pseudomonas_aeruginosa \
  --database db/amrfinder \
  --mutation_all results/amrfinder/point_mutations.tsv \
  --threads 16 \
  --output results/amrfinder/amrfinder.tsv
```

Or run the script, which also writes a `--plus` report:

```bash
pixi run -e annotation bash bin/05_amrfinder.sh
```

Outputs:

| File | Contents |
|---|---|
| `results/amrfinder/amrfinder.tsv` | core AMR hits (the 18-ARG comparison) |
| `results/amrfinder/amrfinder_plus.tsv` | core + stress/virulence "plus" genes |
| `results/amrfinder/point_mutations.tsv` | every mutation considered by `mutation_all` |
| `results/amrfinder/amrfinder.database_version.txt` | database date |

How to read one row of `amrfinder.tsv`:

| Column | Meaning |
|---|---|
| `Gene symbol` | short gene name, e.g. `blaPDC-142` |
| `Element type` | `AMR`, `STRESS`, `VIRULENCE`, ... |
| `Class` / `Subclass` | β-lactam, aminoglycoside, etc. |
| `Method` | `EXACTX`, `BLASTX`, `HMM`, `POINT` |
| `% Coverage` / `% Identity` | how well the hit matches the reference |

The paper reports 18 ARGs, including `blaPDC-142`, `blaPME-1`, `blaOXA-395`,
and the colistin-associated mutations `cprS_E386D`, `cprS_T16S`, `pmrB_A4T`,
`pmrB_G68S`, `pmrB_S2P`, `pmrB_V15I`, `pmrB_Y345H`, `parR_L153R`,
`parR_S170N`, `parS_H398R`.

> AMRFinderPlus only reports point mutations present in its curated database.
> If a gene such as `cprS` is absent from the report, that is a database
> coverage difference, not proof that the mutation is absent. The paper's
> exact mutation list is the benchmark; compare the rows you get and note
> missing ones in the summary.

---

## 7. Cross-check with CARD-RGI 6.0.3

Download CARD data (4.4 MB compressed):

```bash
mkdir -p db/card
curl -fsSL --retry 5 \
  https://card.mcmaster.ca/latest/data \
  -o db/card/card-data.tar.bz2
tar -xjf db/card/card-data.tar.bz2 -C db/card
```

Load it into a local database and run RGI:

```bash
mkdir -p results/rgi
pixi run -e resistome rgi load \
  --card_json db/card/card.json \
  --local

pixi run -e resistome rgi main \
  --input_sequence data/CP196749.1.fasta \
  --output_file results/rgi/strain71 \
  --input_type contig \
  --num_threads 16 \
  --local \
  --clean
```

Or:

```bash
pixi run -e resistome bash bin/06_rgi_card.sh
```

Outputs:

| File | Contents |
|---|---|
| `results/rgi/strain71.txt` | tab-delimited RGI calls |
| `results/rgi/strain71.json` | full RGI data |

Useful RGI columns: `Best_Hit_ARO` (gene), `Cut_Off` (Perfect/Strict/Loose),
`Best_Identities`, `Drug Class`, `Resistance Mechanism`, `AMR Gene Family`.

> RGI 6.0.3 is pinned to match the paper. If a future CARD release changes its
> JSON schema and RGI refuses to load it, update only RGI (`pixi add -e
> resistome rgi=...`) and record the new version. Do not silently mix CARD
> versions between runs.

---

## 8. Virulence context with VFDB and ABRicate

The paper used VFDB through the VFinder website. ABRicate runs the same VFDB
nucleotide database locally, with explicit thresholds. This is a deliberate
simplification: it removes a web service but keeps the database and the
interpretation.

```bash
mkdir -p results/virulence
pixi run -e virulence abricate --setupdb
pixi run -e virulence abricate \
  --db vfdb \
  --minid 90 \
  --mincov 50 \
  --threads 16 \
  data/CP196749.1.fasta \
  > results/virulence/vfdb.tsv
```

Or:

```bash
pixi run -e virulence bash bin/07_vfdb.sh
```

The paper reports 213 virulence factors. ABRicate counts **hits**, and the
VFDB release bundled with ABRicate 1.4.0 is from 2026-Apr-3, so expect a
similar but not necessarily identical number. Report the database date and
the thresholds when you compare.

> `--minid 90 --mincov 50` matches the paper's ARG validation thresholds
> (≥90% identity, ≥50% coverage). If you want stricter VF calls, use
> `--mincov 80` and say so in your write-up.

---

## 9. Build the summary

```bash
pixi run bash bin/08_summarize.sh
```

Outputs:

| File | Contents |
|---|---|
| `results/summary.md` | human-readable tables for genome, ST, ARGs, VFs, tmex |
| `results/summary.tsv` | one metric per row, easy to diff between runs |

The summary script is plain `awk`. Read it — it is a template for extracting
columns from AMRFinderPlus, RGI and ABRicate output without a parser library.

---

## 10. Full run, from zero

```bash
pixi install --all
bash bin/run_all.sh
```

`run_all.sh` calls each step in the right pixi environment and writes a log to
`logs/<step>.log`. If a step fails, the log tells you which tool and which
command. Fix the tool or download, then rerun only that step.

---

## What to compare against the paper

| Paper result | Where to look | Expected |
|---|---|---|
| Genome 6,589,538 bp | `results/summary.md` | exact |
| ST1971 | MLST table | exact |
| 18 ARGs | AMRFinderPlus + RGI tables | count and gene list |
| `blaPDC-142`, `blaPME-1`, `blaOXA-395` | AMRFinderPlus/RGI | present |
| Colistin mutations | `point_mutations.tsv` | compare each gene/variant |
| `tmexCD2–toprJ2` | RGI/AMRFinderPlus grep | present |
| 213 VFs | VFDB table | similar, database-dependent |

Do not force a match by lowering thresholds. Record differences (database
date, tool version, missing gene) in your notes; that is the honest
reproduction.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `pixi: command not found` | `export PATH="$HOME/.pixi/bin:$PATH"` |
| `No valid AMRFinder database` | run `amrfinder_update --database db/amrfinder --force_update` |
| Bakta download stalls | resume with `curl -C -` to `db/bakta-light/db-light.tar.gz`, then extract |
| Bakta says database schema mismatch | remove `db/bakta-light` and download again; do not mix DB versions |
| `mlst` cannot find scheme | use `--scheme paeruginosa`; check `mlst --list` |
| RGI cannot load `card.json` | confirm `db/card/card.json` exists; check RGI/CARD version compatibility |
| `abricate: database not found` | run `abricate --setupdb` |
| Out of disk | genome + light DB + AMR DB + RGI + results ≈ 3 GB; full Bakta DB needs ~40 GB |
| Apple Silicon / macOS | change `platforms` in `pixi.toml` to `osx-arm64`; some pinned Linux builds may not exist |

## Why this is easier than Nextflow/containers

- You can read every command in `bin/` in a few minutes.
- Each tool lives in its own environment; a version conflict cannot break an
  unrelated step.
- Outputs are plain TSV/FASTA/JSON, not hidden inside a `work/` hashed
  directory.
- A failed step is fixed and rerun on its own; there is no scheduler state to
  clean up.
- The trade-off is that you run steps in order yourself. For one sample that
  is an advantage; for 500 samples, use a workflow manager.

---

## References

1. Nguyen QH, et al. *J Glob Antimicrob Resist.* 2026;48:127–130.
   doi:10.1016/j.jgar.2026.03.007.
2. Bakta: Schwengers O, et al. *Microb Genom.* 2021;7(11):000685.
3. AMRFinderPlus: Feldgarden M, et al. *Sci Rep.* 2021;11:12728.
4. CARD-RGI: Alcock BP, et al. *Nucleic Acids Res.* 2023;51:D690–D699.
5. mlst: Seemann T. https://github.com/tseemann/mlst.
6. ABRicate/VFDB: Chen L, et al. *Nucleic Acids Res.* 2016;44:D694–D700.
