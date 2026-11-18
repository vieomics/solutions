#!/usr/bin/env bash
# Step 0b - stage the two large databases from the public OmicsLab workspace.
#
# The public workspace has curated, versioned copies of the AMRFinderPlus and
# CARD databases under references/databases/. They are much faster to download
# than the upstream sites and need no API key. If omx is not installed (for
# example on a local laptop), the script falls back to the tools' own download
# commands.
set -euo pipefail
cd "$(dirname "$0")/.."

WORKSPACE="${OMICSLAB_DATABASE_WORKSPACE:-c669cc81-d096-4679-a9a2-03329167b71f}"
AMRFINDER_DB="${AMRFINDER_DB:-db/amrfinder}"
CARD_DB="${CARD_DB:-db/card}"
mkdir -p "$AMRFINDER_DB" "$CARD_DB" db logs

have_omx=false
if command -v omx >/dev/null 2>&1; then
    have_omx=true
    echo "[databases] omx found; public workspace: $WORKSPACE"
else
    echo "[databases] omx not found; using upstream download commands"
fi

# ---------------------------------------------------------------------------
# AMRFinderPlus reference database
# ---------------------------------------------------------------------------
if [ -s "$AMRFINDER_DB/version.txt" ]; then
    echo "[databases] AMRFinderPlus database already staged: $(cat "$AMRFINDER_DB/version.txt")"
else
    staged=false
    if [ "$have_omx" = true ]; then
        echo "[databases] staging AMRFinderPlus 2025-07-16.1 from OmicsLab ..."
        if omx download references/databases/amrfinderplus/2025-07-16.1 \
                "$AMRFINDER_DB" -w "$WORKSPACE" -y --threads 8; then
            staged=true
        else
            echo "[databases] omx download failed; falling back to NCBI" >&2
        fi
    fi

    if [ "$staged" = false ]; then
        echo "[databases] downloading AMRFinderPlus from NCBI (first run only) ..."
        pixi run -e annotation amrfinder_update \
            --database "$AMRFINDER_DB" --force_update
    fi
fi

# ---------------------------------------------------------------------------
# CARD database for RGI
# ---------------------------------------------------------------------------
if [ -s "$CARD_DB/card.json" ]; then
    echo "[databases] CARD database already staged"
else
    staged=false
    if [ "$have_omx" = true ]; then
        echo "[databases] staging CARD 4.0.2 from OmicsLab ..."
        if omx download references/databases/rgi/card_4.0.2 \
                "$CARD_DB" -w "$WORKSPACE" -y --threads 8; then
            staged=true
        else
            echo "[databases] omx download failed; falling back to card.mcmaster.ca" >&2
        fi
    fi

    if [ "$staged" = false ]; then
        echo "[databases] downloading CARD (first run only) ..."
        rm -f "$CARD_DB/card-data.tar.bz2"
        curl -fsSL --retry 5 --retry-delay 5 --retry-connrefused \
            --connect-timeout 20 --max-time 600 \
            https://card.mcmaster.ca/latest/data -o "$CARD_DB/card-data.tar.bz2"
        tar -xjf "$CARD_DB/card-data.tar.bz2" -C "$CARD_DB"
    fi
fi

AMR_VERSION="$(cat "$AMRFINDER_DB/version.txt" 2>/dev/null || echo NA)"
CARD_VERSION="$(grep -o '"_version": *"[^"]*"' "$CARD_DB/card.json" 2>/dev/null | head -n1 | sed 's/.*"\([^"]*\)"$/\1/' || true)"
CARD_VERSION="${CARD_VERSION:-NA}"

{
    printf 'database\tversion\tsource\tstaged_utc\n'
    printf 'AMRFinderPlus\t%s\tOmicsLab public workspace references/databases/amrfinderplus\t%s\n' \
        "$AMR_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'CARD\t%s\tOmicsLab public workspace references/databases/rgi\t%s\n' \
        "$CARD_VERSION" "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > db/database_sources.tsv

echo "[databases] AMRFinderPlus: $AMR_VERSION"
echo "[databases] CARD:          $CARD_VERSION"
echo "[databases] wrote db/database_sources.tsv"
