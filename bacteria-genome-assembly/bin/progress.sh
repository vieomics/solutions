#!/usr/bin/env bash
# Status snapshot for the fetchngs run in this repo.
# Usage: bash bin/progress.sh          (one snapshot)
#        watch -n 30 bash bin/progress.sh   (live-ish tracking)
set -uo pipefail
cd "$(dirname "$0")/.."
LOG="${1:-logs/fetchngs.log}"

strip_ansi() { sed -r 's/\x1B\[[0-9;]*[A-Za-z]//g; s/\x1B\[[0-9;]*m//g'; }

echo "=== $(date '+%F %T') ==="

echo
echo "--- SLURM jobs (our pipelines) ---"
squeue -u "${USER}" -o "%.8i %.20j %.2t %.10M %.6D %R" 2>/dev/null \
  | grep -E "JOBID|nf-" || echo "(none)"

echo
echo "--- Nextflow log (last 12 lines) ---"
[ -f "$LOG" ] && tail -n 12 "$LOG" | strip_ansi

echo
echo "--- FASTQ files in work/ (in progress + completed tasks) ---"
find work -name "*.fastq.gz" -type f -exec ls -lh {} \; 2>/dev/null \
  | awk '{printf "%-8s %s\n", $5, $9}' | sed -E 's|work/[^/]+/||' || true
echo "work/ total: $(du -sh work 2>/dev/null | cut -f1)"

echo
echo "--- Published results ---"
find results/fetchngs -maxdepth 2 -type d 2>/dev/null | sort
echo "published fastq.gz: $(find results/fetchngs -name '*.fastq.gz' 2>/dev/null | wc -l)"
echo "results/ total: $(du -sh results 2>/dev/null | cut -f1)"

echo
echo "--- Download containers running ---"
docker ps --format '{{.Image}}' 2>/dev/null | grep -c gzip_wget \
  | xargs -I{} echo "gzip_wget containers: {}"
