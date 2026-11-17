#!/usr/bin/env bash
# Circular-aware mapping and consensus for the five study samples.
#
# viralrecon uses Bowtie2 against a linear reference.  Here we additionally
# map trimmed reads to an origin-extended reference with BWA-MEM, project
# positions modulo the genome length, and patch boundary Ns in the viralrecon
# consensus.  This is the branch that provides mapping/depth/coverage outputs
# for the downstream comparative analysis.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

THREADS="${THREADS:-8}"
META="metadata/selected_samples.tsv"
REF="references/hbv_reference.fasta"
EXT="references/hbv_reference.extended.fasta"
VIRALRECON_CONSENSUS="results/viralrecon/variants/bcftools/consensus/bcftools"

mkdir -p results/trimmed results/mapping results/consensus logs

if [[ ! -s "${EXT}" ]]; then
  python bin/make_extended_reference.py
fi
if [[ ! -s "${EXT}.bwt" ]]; then
  bwa index "${EXT}"
fi

tail -n +2 "${META}" | tr -d '\r' | while IFS=$'\t' read -r sample run exp sample_acc alias genotype country date instrument reads f1 f2 md5_1 md5_2; do
  echo "=== ${sample} ==="
  R1="data/fastq/${sample}_R1.fastq.gz"
  R2="data/fastq/${sample}_R2.fastq.gz"
  T1="results/trimmed/${sample}_R1.fastq.gz"
  T2="results/trimmed/${sample}_R2.fastq.gz"

  fastp \
    --in1 "${R1}" --in2 "${R2}" \
    --out1 "${T1}" --out2 "${T2}" \
    --cut_front --cut_tail --trim_poly_x \
    --cut_mean_quality 30 --qualified_quality_phred 30 \
    --unqualified_percent_limit 10 --length_required 50 \
    --thread "${THREADS}" \
    --json "results/trimmed/${sample}.fastp.json" \
    --html "results/trimmed/${sample}.fastp.html" \
    --report_title "HBV ${sample} fastp report" \
    > "logs/${sample}.fastp.log" 2>&1

  bwa mem -t "${THREADS}" \
    -R "@RG\tID:${sample}\tSM:${sample}\tPL:ILLUMINA" \
    "${EXT}" "${T1}" "${T2}" 2> "results/mapping/${sample}.bwa.log" \
    | samtools sort -@ 2 -m 1G -o "results/mapping/${sample}.sorted.bam" -

  samtools index "results/mapping/${sample}.sorted.bam"
  samtools flagstat "results/mapping/${sample}.sorted.bam" > "results/mapping/${sample}.flagstat.txt"
  samtools stats "results/mapping/${sample}.sorted.bam" > "results/mapping/${sample}.samtools_stats.txt"
  samtools idxstats "results/mapping/${sample}.sorted.bam" > "results/mapping/${sample}.idxstats.txt"

  python bin/circular_consensus.py \
    --bam "results/mapping/${sample}.sorted.bam" \
    --reference "${REF}" \
    --sample "${sample}" \
    --outdir results/consensus \
    --viralrecon-consensus "${VIRALRECON_CONSENSUS}/${sample}.consensus.fa" \
    > "logs/${sample}.circular.log" 2>&1

  cp "${VIRALRECON_CONSENSUS}/${sample}.filtered.vcf.gz" "results/consensus/${sample}.vcf.gz"
  cp "${VIRALRECON_CONSENSUS}/${sample}.filtered.vcf.gz.tbi" "results/consensus/${sample}.vcf.gz.tbi"
  cp "${VIRALRECON_CONSENSUS}/${sample}.consensus.fa" "results/consensus/${sample}.viralrecon.consensus.fasta"
  cat "logs/${sample}.circular.log"
done
