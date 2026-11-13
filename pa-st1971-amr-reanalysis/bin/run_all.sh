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
    local name="$1" env="$2" script="$3"
    echo
    echo "======================================================================"
    echo "[$(date '+%F %T')] $name"
    echo "======================================================================"
    if [ "$env" = "default" ]; then
        pixi run bash "$script" 2>&1 | tee "logs/${name}.log"
    else
        pixi run -e "$env" bash "$script" 2>&1 | tee "logs/${name}.log"
    fi
}

bash bin/00_check_env.sh | tee logs/00_check_env.log
run_step 01_download default    bin/01_download_genome.sh
run_step 02_qc       default    bin/02_genome_qc.sh
run_step 03_bakta    annotation bin/03_annotate.sh
run_step 04_mlst     typing     bin/04_mlst.sh
run_step 05_amrfinder annotation bin/05_amrfinder.sh
run_step 06_rgi      resistome  bin/06_rgi_card.sh
run_step 07_vfdb     virulence  bin/07_vfdb.sh
run_step 08_summary  default    bin/08_summarize.sh

echo
echo "[done] open results/summary.md"
