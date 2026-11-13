#!/usr/bin/env bash
# Step 0 - verify that pixi has installed every environment.
set -euo pipefail
cd "$(dirname "$0")/.."

echo "pixi: $(pixi --version)"
echo

check() {
    local label="$1" cmd="$2"
    printf '%-22s ' "$label"
    if eval "$cmd" >/tmp/pa-st1971-check.$$ 2>&1; then
        tail -n 1 /tmp/pa-st1971-check.$$
    else
        echo "MISSING (run: pixi install --all)"
        rm -f /tmp/pa-st1971-check.$$
        return 1
    fi
    rm -f /tmp/pa-st1971-check.$$
}

check "seqkit"     "pixi run seqkit version"
check "bakta"      "pixi run -e annotation bakta --version"
check "amrfinder"  "pixi run -e annotation amrfinder --version"
check "mlst"       "pixi run -e typing mlst --version"
check "rgi"        "pixi run -e resistome rgi --version"
check "abricate"   "pixi run -e virulence abricate --version"

echo
echo "All environments look good. Next: bash bin/run_all.sh"
