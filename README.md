# vieomics/solutions

A small collection of reproducible bioinformatics solutions. Each solution is
self-contained in its own folder, with its own README, environment, scripts and
write-up.

| Solution | What it covers |
|---|---|
| [bacteria-genome-assembly](bacteria-genome-assembly/) | Bacterial genome assembly with `nf-core/bacass`, read-level reanalysis of `blaNDM` truncations in ENA PRJEB86571, and a per-sample OmicsLab job workflow. |

## Layout

```text
solutions/
├── README.md
└── bacteria-genome-assembly/
    ├── README.md
    ├── analysis/
    ├── bin/
    ├── conf/
    ├── docs/
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
