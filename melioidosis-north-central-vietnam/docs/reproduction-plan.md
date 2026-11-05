# Reproduction plan — Norris et al. (2026)

## 1. Scope

Reproduce the public-data analysis of:

> Norris MH, Au La TH, Metrailer MC, et al. (2026). Expanding the molecular
> epidemiology of melioidosis in North Central Vietnam. *PLOS Neglected Tropical
> Diseases* 20(2): e0013945.
> [doi:10.1371/journal.pntd.0013945](https://doi.org/10.1371/journal.pntd.0013945)

The paper is an **isolate WGS** study, not a metagenomics study. Soil samples
were cultured isolates. The paper used `nf-core/bacass` (FastP, Unicycler,
Prokka), not `nf-core/mag`.

The reproduction has two scales:

1. **Core reproduction:** the 47 newly sequenced isolates in SRA
   `PRJNA1180080`.
2. **Full comparative reproduction:** 1,468 genomes total, including the 47 new
   isolates, for the paper's Fig 2 SNP/cgMLST trees.

## 2. Data preparation

### 2.1 New isolates — 47 runs

Verified from ENA/SRA:

| Item | Value |
|---|---|
| BioProject | `PRJNA1180080` |
| Runs | 47 paired Illumina MiSeq runs |
| Clinical / soil / animal | 35 / 10 / 2 |
| Total bases | ~29.5 Gb |
| Total spots | ~100.1 M |
| Approx. gzipped FASTQ | ~14.7 GB |
| First test run | `SRR31184429` (`Bp52_TY01`, animal) |

The accession list is [`../ids.csv`](../ids.csv). The one-run test list is
[`../ids.single.csv`](../ids.single.csv).

### 2.2 One-sample fetchngs test

Run `nf-core/fetchngs` 1.13.0 for `SRR31184429` before attempting all 47.

- Download method: `sratools` (ENA HTTPS/FTP was unreachable from this
  environment; the NDM solution also found ENA throttling).
- Suggested first-run resources: 4 CPU, 8 GB RAM, 100 GB disk, 1 hour.
- Suggested output prefix:
  `s3://vieomics-prod/data/datasets/gianglabs/47-samples/fetchngs-test/SRR31184429/`
- Verify:
  - both R1 and R2 FASTQ files exist;
  - gzip files are readable;
  - sample ID and run accession match `SRR31184429`;
  - output samplesheet has one row;
  - file count and approximate size match the ENA report.

If the one-sample job succeeds, run all 47 with the same pipeline and method.

### 2.3 Comparative dataset — 1,468 runs

The paper's S1 Table was checked:

- Columns: `SRA`, `Strain`, `Host`, `Country`, `Continent`,
  `Collection_Date`, `ST`.
- **No FASTA or assembly column.** The comparative genomes are raw SRA reads
  and must be downloaded and assembled, as described in the paper.
- The table currently has 1,493 rows and 1,492 unique SRA accessions, while the
  paper text says 1,468. Reconcile this difference before the full comparative
  run (duplicates, failed runs, or excluded genomes).

Because the workspace quota is 100 GiB, the full 1,468-run FASTQ set does not
fit. Options:

1. process in batches and delete FASTQs after assembly;
2. use an external bucket or a larger workspace quota;
3. derive assemblies first, then keep only assemblies and annotations.

## 3. bacass assembly

### 3.1 Version

The paper cites `nf-core/bacass` v2.1.0. The existing OmicsLab baseline and cost
data use **2.6.1**. Recommendation:

- use **2.6.1** for the first reproduction because it matches the five
  completed jobs and the platform cost baseline;
- record the version difference;
- if exact version fidelity is required, run a small 2.1.0 comparison after
  the 47-sample run.

### 3.2 Samplesheet

bacass expects:

```text
ID	R1	R2	LongFastQ	Fast5	GenomeSize
```

For the 47-sample run:

- `ID`: paper isolate name (for example `Bp52_TY01`), not only `SRR31184429`.
- `R1`, `R2`: absolute `s3://...fastq.gz` paths.
- `LongFastQ`, `Fast5`: `NA`.
- `GenomeSize`: `NA`.

### 3.3 Changes from the one-sample runs

| Setting | One-sample baseline | 47-sample run |
|---|---|---|
| `params.input` | one-row TSV | 47-row TSV |
| `params.outdir` | one prefix | one dataset/job prefix |
| CPU | 16 | 32 recommended |
| Memory | 32 GB | 64 GB recommended |
| Disk | 100 GB | 300 GB recommended |
| Time | 1 h | 8–12 h, or split into batches |
| `assembly_type` | `short` | `short` |
| `assembler` | `unicycler` | `unicycler` |
| `unicycler_args` | test-profile bold/only-assembler | empty/default, as in the paper |
| `skip_annotation` | false | false — Prokka GFF3 needed for Roary |
| `skip_kraken2` | false | true — not used in the paper |
| `skip_kmerfinder` | false | true — not used in the paper |
| `skip_busco` | false | true — not used in the paper |
| `skip_pycoqc` | false | true — short reads only |
| `skip_polish` | false | true — short-read assemblies |
| `save_trimmed` | false | false, to limit disk use |

The pipeline itself does not need code changes for 47 samples. The existing
one-job-per-sample helper should not be used unchanged; use one 47-row job or
split into batches.

### 3.4 Recommended run order

1. Pilot 5 samples (one clinical, one soil, one animal, plus two others) with
   the proposed 32 CPU / 64 GB / 300 GB / 8 h shape.
2. Record runtime, peak disk, and peak memory.
3. Run all 47 in one job if the pilot stays below about half the time and disk
   limits; otherwise split into four batches of about 12.

## 4. Downstream analysis

1. **Assembly QC:** contig count, total length, N50, coverage.
2. **MLST:** seven-locus pubMLST scheme; check the paper's ST assignments
   (including ST41 enrichment and new STs).
3. **cgMLST:** chewBBACA with the pubMLST *B. pseudomallei* schema; cgST
   assignment.
4. **Whole-genome SNP phylogeny:** PhaME against *B. pseudomallei* 1026b
   (`GCA_000260515`), then IQ-TREE.
5. **Pan-genome:** Roary on the 21 ST41 isolates plus 41 non-ST41 comparators;
   confirm the ~15.4 kb ST41-specific region.
6. **Validation against the paper:** ST41 frequency (21/35 clinical), new STs,
   ST41 soil match, ST55 pig/soil match, and the Fig 2/3/4 clustering patterns.

## 5. Cost estimate

Based on the five latest completed OmicsLab bacass jobs:

| Job | Runtime | Cost (VND) |
|---|---:|---:|
| `omicslab-ijm4jx` | 19m 23s | 3,184 |
| `bacass-ERR14693661-r2` | 29m 13s | 4,719 |
| `bacass-ERR14693662-r2` | 40m 25s | 6,412 |
| `bacass-ERR14693663` | 30m 40s | 4,886 |
| `bacass-ERR14693664` | 31m 19s | 5,005 |
| **Average** | **30.2 min** | **4,841** |

Approximate costs at ~26,000 VND/USD:

| Scope | Estimate |
|---|---:|
| 47 new genomes | ~228,000 VND (~$9) |
| 47 with 25% contingency | ~284,000 VND (~$11) |
| 1,468 genomes | ~7.11 M VND (~$273) |
| 1,468 with 25% contingency | ~8.88 M VND (~$342) |

These are compute estimates only. They exclude S3 storage/egress and downstream
MLST/cgMLST/PhaME/Roary compute (roughly 0.1–1 M VND until benchmarked).

## 6. Storage constraints

- Workspace quota: **100 GiB**.
- Currently used: ~8.3 GB.
- 47 FASTQs: ~15 GB, fits.
- 1,468 FASTQs: likely 0.5–1 TB, does not fit.

The full comparative run therefore needs a storage plan before launch.

## 7. Risks and open questions

- **S1 Table count:** 1,493 rows / 1,492 unique accessions vs 1,468 in the text.
- **bacass version:** paper v2.1.0 vs platform baseline v2.6.1.
- **Profile override:** `test_full` sets `unicycler_args` to bold/only-assembler;
  confirm the manifest params override it to the paper's default.
- **ENA/FTP access:** blocked here; use `sratools` or Aspera.
- **Aspera:** port 33001 is reachable, but the `ascp` client is not available
  through pixi/conda and must be installed separately. fetchngs with
  `sratools` is the simpler first test.
- **Storage:** full 1,468-genome run exceeds the current workspace quota.

## 8. Acceptance criteria for the first PR

- New solution folder with README, plan, `ids.csv`, and `ids.single.csv`.
- pixi environment present and installable.
- One-sample fetchngs job launched on OmicsLab and output verified.
- No production data deleted or overwritten.
