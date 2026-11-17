#!/usr/bin/env bash
# Download the five selected PRJNA659786 runs from OmicsLab storage and verify
# each file against the ENA/SRA MD5 recorded in metadata/selected_samples.tsv.
#
# The OmicsLab CLI resolves paths relative to the storage prefix configured for
# the workspace.  Run `omx pwd` first; it must point at
# datasets/gianglabs/PRJNA659786 (or use `omx cd datasets/gianglabs/PRJNA659786`).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
META="${ROOT}/metadata/selected_samples.tsv"
OUT="${ROOT}/data/fastq"
mkdir -p "${OUT}"

command -v omx >/dev/null || { echo "omx not found in PATH" >&2; exit 1; }

tail -n +2 "${META}" | tr -d '\r' | while IFS=$'\t' read -r sample run exp sample_acc alias genotype country date instrument reads f1 f2 md5_1 md5_2; do
  for mate in 1 2; do
    src="${exp}_${run}_${mate}.fastq.gz"
    dst="${OUT}/${sample}_R${mate}.fastq.gz"
    expected="${md5_1}"
    [[ "${mate}" == "2" ]] && expected="${md5_2}"

    if [[ -s "${dst}" ]] && [[ "$(md5sum "${dst}" | cut -d' ' -f1)" == "${expected}" ]]; then
      echo "[skip] ${dst} (md5 ok)"
      continue
    fi

    echo "[download] ${src} -> ${dst}"
    omx download "fastq/${src}" "${dst}"
    got="$(md5sum "${dst}" | cut -d' ' -f1)"
    if [[ "${got}" != "${expected}" ]]; then
      echo "MD5 mismatch for ${dst}: expected ${expected}, got ${got}" >&2
      exit 1
    fi
    echo "[ok] ${dst} md5=${got}"
  done
done

echo "All selected FASTQ files downloaded and verified."
