#!/usr/bin/env bash
# Verify the five FASTQ pairs without downloading or modifying them.
# Checks gzip integrity and the ENA/SRA MD5 recorded in selected_samples.tsv.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

failed=0
while IFS=$'\t' read -r sample run exp sample_acc alias genotype country date instrument reads f1 f2 md5_1 md5_2; do
  for mate in 1 2; do
    path="data/fastq/${sample}_R${mate}.fastq.gz"
    expected="${md5_1}"
    [[ "${mate}" == "2" ]] && expected="${md5_2}"
    if [[ ! -s "${path}" ]]; then
      echo "MISSING ${path}"
      failed=1
      continue
    fi
    if ! gzip -t "${path}" 2>/dev/null; then
      echo "GZIP_FAIL ${path}"
      failed=1
      continue
    fi
    got="$(md5sum "${path}" | cut -d' ' -f1)"
    if [[ "${got}" != "${expected}" ]]; then
      echo "MD5_FAIL ${path} expected=${expected} got=${got}"
      failed=1
    else
      echo "OK ${path}"
    fi
  done
done < <(tail -n +2 metadata/selected_samples.tsv | tr -d '\r')

if [[ "${failed}" -ne 0 ]]; then
  echo "FASTQ verification failed" >&2
  exit 1
fi
echo "All five FASTQ pairs are intact and match the ENA/SRA MD5 values."
