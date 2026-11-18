#!/usr/bin/env bash
# Run the whole single-sample workflow from start to finish.
#
# Each step uses the smallest pixi environment that contains its tools. That
# keeps the paper's pinned versions from fighting with each other, and shows a
# beginner how to isolate tools without containers.
set -euo pipefail
cd "$(dirname "$0")/.."

export THREADS="${THREADS:-16}"
mkdir -p logs

run_step() {
    local name="$1" env="$2"
    shift 2
    echo
    echo "======================================================================"
    echo "[$(date '+%F %T')] $name"
    echo "======================================================================"
    if [ "$env" = "default" ]; then
        pixi run "$@" 2>&1 | tee "logs/${name}.log"
    else
        pixi run -e "$env" "$@" 2>&1 | tee "logs/${name}.log"
    fi
}

bash bin/00_check_env.sh | tee logs/00_check_env.log
run_step 00b_databases default    bash bin/00_stage_databases.sh
run_step 01_download   default    bash bin/01_download_genome.sh
run_step 02_qc         default    bash bin/02_genome_qc.sh
run_step 03_annotation annotation bash bin/03_annotate.sh
run_step 04_mlst       typing     bash bin/04_mlst.sh
run_step 05_amrfinder  annotation bash bin/05_amrfinder.sh
run_step 06_rgi        resistome  bash bin/06_rgi_card.sh
run_step 07_vfdb       virulence  bash bin/07_vfdb.sh
run_step 08_summary    default    bash bin/08_summarize.sh
run_step 09_figures    viz        python bin/09_figures.py
run_step 10_manifests  default    bash bin/10_manifest.sh

echo
echo "[done] open results/summary.md"
