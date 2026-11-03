#!/usr/bin/env bash
# Download the Apptainer images needed by nf-core/bacass from the local S3 mirror.
#
# Usage:
#   bash bin/fetch_images.sh [TARGET_DIR]        # default: .apptainer-cache
#   pixi run fetch-images
#
# The file names must match Nextflow's Apptainer cache naming convention
# (image URL with ':' and '/' replaced by '-').
set -euo pipefail

S3_ENDPOINT="${S3_ENDPOINT:-https://s3-hcm-r2.s3cloud.vn}"
S3_BUCKET="${S3_BUCKET:-s3://omicslab/data/images}"
TARGET="${1:-.apptainer-cache}"

mkdir -p "$TARGET"

IMAGES=(
    # fastqc + fastp (read QC)
    "quay.io-biocontainers-fastqc-0.12.1--hdfd78af_0.img"
    "community.wave.seqera.io-library-fastp-1.0.1--c8b87fe62dcc103c.img"
    # assembly + assembly QC
    "community.wave.seqera.io-library-unicycler-0.5.1--b9d21c454db1e56b.img"
    "community.wave.seqera.io-library-quast-5.3.0--755a216045b6dbdd.img"
    "community.wave.seqera.io-library-busco_sepp-f2dbc18a2f7a5b64.img"
    # contamination checks
    "community.wave.seqera.io-library-kraken2_coreutils_pigz-920ecc6b96e2ba71.img"
    "quay.io-biocontainers-kmerfinder-3.0.2--hdfd78af_0.img"
    # helper image used by nf-core local modules
    "quay.io-nf-core-ubuntu-20.04.img"
)

for img in "${IMAGES[@]}"; do
    if [[ -s "$TARGET/$img" ]]; then
        echo "cached   $img"
        continue
    fi
    echo "fetching $img"
    aws s3 cp --no-sign-request --only-show-errors \
        "$S3_BUCKET/$img" "$TARGET/$img" \
        --endpoint-url "$S3_ENDPOINT"
done

echo "done -> $TARGET"
