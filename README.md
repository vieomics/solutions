# vieomics/solutions

A small collection of reproducible bioinformatics solutions. Each solution is
self-contained in its own folder, with its own README, environment, scripts and
write-up.

| Solution | What it covers |
|---|---|
| [ndm-truncation-reanalysis](ndm-truncation-reanalysis/) | Read-level reanalysis of the reported `blaNDM` truncations in Dung et al. 2025 (ENA PRJEB86571), with `nf-core/bacass` assembly and a per-sample OmicsLab job workflow. |

## Layout

```text
solutions/
├── README.md
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
