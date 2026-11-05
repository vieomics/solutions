# vieomics/solutions

A small collection of reproducible bioinformatics solutions. Each solution is
self-contained in its own folder, with its own README, environment, scripts and
write-up.

| Solution | What it covers |
|---|---|
| [melioidosis-north-central-vietnam](melioidosis-north-central-vietnam/) | Reproduction plan for Norris et al. (2026), *PLOS Neglected Tropical Diseases* — [doi:10.1371/journal.pntd.0013945](https://doi.org/10.1371/journal.pntd.0013945). 47 new *Burkholderia pseudomallei* genomes plus the paper's 1,468-genome comparative set. |
| [ndm-truncation-reanalysis](ndm-truncation-reanalysis/) | Read-level reanalysis of the reported `blaNDM` truncations in Dung et al. (2025), *Annals of Clinical Microbiology and Antimicrobials* — [doi:10.1186/s12941-025-00818-3](https://doi.org/10.1186/s12941-025-00818-3). Includes `nf-core/bacass` assembly and a per-sample OmicsLab job workflow. |

## Layout

```text
solutions/
├── README.md
├── melioidosis-north-central-vietnam/
│   ├── README.md
│   ├── conf/
│   ├── docs/
│   ├── ids.csv
│   ├── ids.single.csv
│   ├── pixi.toml
│   └── pixi.lock
└── ndm-truncation-reanalysis/
    ├── README.md
    ├── analysis/
    ├── bin/
    ├── conf/
    ├── docs/
    ├── manifests/
    ├── params/
    ├── samplesheets/
    ├── pixi.toml
    └── pixi.lock
```

## Adding a solution

1. Create a folder named after the question or dataset, for example
   `some-new-analysis/`.
2. Give it a `README.md` that states the question, the data, and the exact
   reproduction steps.
3. Keep the environment with the solution (`pixi.toml`, `pixi.lock`), not at
   the repository root.
4. Put long-form write-ups and figures in `docs/`.
5. Keep generated outputs (`results/`, `work/`, `.pixi/`) out of git.

The root `.gitignore` covers the common generated paths for every solution;
each solution may add its own `.gitignore` for local exceptions.
