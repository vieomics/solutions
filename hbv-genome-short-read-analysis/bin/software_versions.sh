#!/usr/bin/env bash
# Record the exact tools used by the two pixi environments.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"
mkdir -p results

version_of() {
  "$@" 2>&1 | head -n 1 | sed 's/[[:space:]]\+/ /g' | sed 's/^ //; s/ $//'
}

{
  printf 'tool\tversion\tenvironment\n'
  printf 'pixi\t%s\tbase\n' "$(pixi --version | awk '{print $2}')"
  printf 'nextflow\t%s\tdefault\n' "$(nextflow -version 2>&1 | awk '/version/ {print $2; exit}')"
  printf 'nextflow\t%s\tviralrecon\n' "$(pixi run -e viralrecon nextflow -version 2>&1 | awk '/version/ {print $2; exit}')"
  printf 'nf-core/viralrecon\t2.6.0\tviralrecon\n'
  printf 'fastqc\t%s\tdefault\n' "$(fastqc --version 2>&1 | sed 's/FastQC v//')"
  printf 'fastqc\t%s\tviralrecon\n' "$(pixi run -e viralrecon fastqc --version 2>&1 | sed 's/FastQC v//')"
  printf 'fastp\t%s\tdefault\n' "$(fastp --version 2>&1 | sed 's/fastp //')"
  printf 'bwa\t%s\tdefault\n' "$(bwa 2>&1 | awk '/Version/ {print $2; exit}')"
  printf 'samtools\t%s\tdefault\n' "$(samtools --version 2>&1 | head -1 | awk '{print $2}')"
  printf 'bcftools\t%s\tdefault\n' "$(bcftools --version 2>&1 | head -1 | awk '{print $2}')"
  printf 'bowtie2\t%s\tdefault\n' "$(bowtie2 --version 2>&1 | head -1 | sed 's/.*version //')"
  printf 'bowtie2\t%s\tviralrecon\n' "$(pixi run -e viralrecon bowtie2 --version 2>&1 | head -1 | sed 's/.*version //')"
  printf 'fastp\t%s\tviralrecon\n' "$(pixi run -e viralrecon fastp --version 2>&1 | sed 's/fastp //')"
  printf 'samtools\t%s\tviralrecon\n' "$(pixi run -e viralrecon samtools --version 2>&1 | head -1 | awk '{print $2}')"
  printf 'bcftools\t%s\tviralrecon\n' "$(pixi run -e viralrecon bcftools --version 2>&1 | head -1 | awk '{print $2}')"
  printf 'multiqc\t%s\tdefault\n' "$(multiqc --version 2>&1 | sed 's/multiqc, version //')"
  printf 'multiqc\t%s\tviralrecon\n' "$(pixi run -e viralrecon multiqc --version 2>&1 | sed 's/multiqc, version //')"
  printf 'mafft\t%s\tdefault\n' "$(mafft --version 2>&1 | sed 's/^v//')"
  printf 'iqtree2\t%s\tdefault\n' "$(iqtree2 --version 2>&1 | head -1 | awk '{print $4}' | sed 's/^v//')"
  printf 'bedtools\t%s\tdefault\n' "$(bedtools --version 2>&1 | sed 's/bedtools v//')"
  printf 'seqkit\t%s\tdefault\n' "$(seqkit version 2>&1 | sed 's/seqkit v//')"
  printf 'phipack\t1.1\tdefault\n'
  printf 'python\t%s\tdefault\n' "$(python --version 2>&1 | sed 's/Python //')"
  printf 'biopython\t%s\tdefault\n' "$(python -c 'import Bio; print(Bio.__version__)')"
  printf 'pysam\t%s\tdefault\n' "$(python -c 'import pysam; print(pysam.__version__)')"
  printf 'matplotlib\t%s\tdefault\n' "$(python -c 'import matplotlib; print(matplotlib.__version__)')"
} > results/software_versions.tsv

sha256sum pixi.lock pixi.toml > results/pixi_checksums.txt
column -t -s$'\t' results/software_versions.tsv
