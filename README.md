# vieomics/solutions

A small collection of reproducible bioinformatics solutions. Each solution is
self-contained in its own folder, with its own README, environment, scripts and
write-up.

| Solution | What it covers |
|---|---|
| [hbv-genome-short-read-analysis](hbv-genome-short-read-analysis/) | Reproducible whole-genome analysis of five Illumina HBV runs from PRJNA659786 plus ten curated GenBank references: nf-core/viralrecon, circular-genome mapping, MAFFT, IQ-TREE 2, recombination screening, overlapping-ORF variant annotation, figures and summary tables. |
| [pa-st1971-amr-reanalysis](pa-st1971-amr-reanalysis/) | Single-sample AMR reanalysis of *Pseudomonas aeruginosa* ST1971 from Nguyen et al. (2026) — [doi:10.1016/j.jgar.2026.03.007](https://doi.org/10.1016/j.jgar.2026.03.007). Starts from `CP196749.1`, stages AMRFinderPlus/CARD databases from the public OmicsLab workspace, and runs MLST, AMRFinderPlus, CARD-RGI and VFDB with committed results, figures and summary tables. |
| [ndm-truncation-reanalysis](ndm-truncation-reanalysis/) | Read-level reanalysis of the reported `blaNDM` truncations in Dung et al. (2025), *Annals of Clinical Microbiology and Antimicrobials* — [doi:10.1186/s12941-025-00818-3](https://doi.org/10.1186/s12941-025-00818-3). Includes `nf-core/bacass` assembly and a per-sample OmicsLab job workflow. |

## Layout

```text
solutions/
├── README.md
├── hbv-genome-short-read-analysis/
│   ├── README.md
│   ├── metadata/
│   ├── references/
│   ├── results/
│   ├── manifests/
│   └── pixi.toml / pixi.lock
├── pa-st1971-amr-reanalysis/
│   ├── README.md
│   ├── metadata/
│   ├── bin/
│   ├── results/
│   ├── manifests/
│   └── pixi.toml / pixi.lock
└── ndm-truncation-reanalysis/
    ├── README.md
    ├── analysis/
    ├── bin/
    ├── conf/
    ├── docs/
    ├── manifests/
    ├── params/
    ├── samplesheets/
    └── pixi.toml / pixi.lock
```

## Adding a solution

1. Create a folder named after the question or dataset, for example
   `some-new-analysis/`.
2. Give it a `README.md` that states the question, the data, and the exact
   reproduction steps.
3. Keep the environment with the solution (`pixi.toml`, `pixi.lock`), not at
   the repository root.
4. Prefer a single `README.md` walkthrough that a beginner can follow from
   inputs to results; put long background notes and figures in `docs/` only
   when they do not fit the main guide.
5. Commit a small reference result set under `results/` when it is part of the
   walkthrough (the HBV and PA solutions do this). Keep large or generated
   artifacts out of git: databases, raw reads, BAMs, `work/`, `.pixi/` and
   caches. Explain what is committed in `results/README.md` and summarise the
   key tables in `manifests/`.

The root `.gitignore` covers the common generated paths for every solution;
each solution may add its own `.gitignore` for local exceptions.
