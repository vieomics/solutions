#!/usr/bin/env nextflow
// Read-level blaNDM integrity audit (H1-H4) for all isolates in parallel.
//
// Usage:
//   pixi run -e analysis nextflow run analysis/ndm_audit.nf \
//       -process.executor local -resume

nextflow.enable.dsl = 2

params.samplesheet    = 'analysis/ndm_audit_samplesheet.tsv'
params.ndm_ref        = 'analysis/test/ndm_ref.fasta'
params.summary_script = 'bin/ndm_audit_summary.py'
params.outdir         = 'results/ndm_audit'

process NDM_AUDIT {
    tag "$sample"
    cpus 8
    memory 8.GB
    publishDir params.outdir, mode: 'copy'

    input:
    tuple val(sample), path(r1), path(r2)
    path ref
    path summary_script

    output:
    tuple val(sample), path("${sample}.summary.tsv"), emit: summaries
    path "${sample}.depth"

    script:
    """
    cp ${ref} ndm_ref.fasta
    bwa index ndm_ref.fasta >/dev/null 2>&1
    bwa mem -t ${task.cpus} ndm_ref.fasta ${r1} ${r2} 2>/dev/null \\
        | samtools sort -@ ${task.cpus} -o ${sample}.bam
    samtools index ${sample}.bam
    samtools depth -a ${sample}.bam > ${sample}.depth
    python3 ${summary_script} ${sample} ${sample}.bam ${sample}.depth > ${sample}.summary.tsv
    """
}

workflow {
    samples = Channel.fromPath(params.samplesheet)
        .splitCsv(header: true, sep: '\t')
        .map { row -> tuple(row.sample, file(row.r1), file(row.r2)) }

    NDM_AUDIT(samples, file(params.ndm_ref), file(params.summary_script))
}
