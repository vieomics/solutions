nextflow.enable.dsl = 2

/*
 * HBV downstream workflow.
 *
 * This workflow starts from the raw FASTQ files and the nf-core/viralrecon
 * consensus output.  The viralrecon run itself is kept as a separate pinned
 * command because it is an upstream nf-core pipeline; this workflow implements
 * the circular mapping, comparative alignment, phylogeny and mutation steps.
 */

params.input            = "${launchDir}/samplesheet.csv"
params.reference        = "${launchDir}/references/hbv_reference.fasta"
params.extended_reference = "${launchDir}/references/hbv_reference.extended.fasta"
params.public_fasta     = "${launchDir}/references/hbv_public_genomes.fasta"
params.public_metadata  = "${launchDir}/references/hbv_metadata.tsv"
params.sample_metadata  = "${launchDir}/metadata/selected_samples.tsv"
params.viralrecon_dir   = "${launchDir}/results/viralrecon"
params.outdir           = "${launchDir}/results_nf"
params.script_dir       = "${projectDir}/../bin"
params.cpus             = 8

process FASTP {
    tag "$sample"
    cpus 4
    memory '2 GB'
    publishDir "${params.outdir}/trimmed", mode: 'copy', pattern: '*.trimmed_R*.fastq.gz', saveAs: { filename -> filename.replace('.trimmed', '') }
    publishDir "${params.outdir}/trimmed", mode: 'copy', pattern: '*.{json,html}'

    input:
    tuple val(sample), path(r1), path(r2)

    output:
    tuple val(sample), path("${sample}.trimmed_R1.fastq.gz"), path("${sample}.trimmed_R2.fastq.gz"), emit: reads
    path("${sample}.fastp.json"), emit: json
    path("${sample}.fastp.html"), emit: html

    script:
    """
    fastp \\
        --in1 ${r1} --in2 ${r2} \\
        --out1 ${sample}.trimmed_R1.fastq.gz --out2 ${sample}.trimmed_R2.fastq.gz \\
        --cut_front --cut_tail --trim_poly_x \\
        --cut_mean_quality 30 --qualified_quality_phred 30 \\
        --unqualified_percent_limit 10 --length_required 50 \\
        --thread ${task.cpus} \\
        --json ${sample}.fastp.json --html ${sample}.fastp.html \\
        --report_title "HBV ${sample} fastp report"
    """
}

process BWA_INDEX {
    cpus 2
    memory '1 GB'

    input:
    path reference

    output:
    path 'bwa_index', emit: index

    script:
    """
    mkdir bwa_index
    cp ${reference} bwa_index/reference.fasta
    bwa index bwa_index/reference.fasta
    """
}

process BWA_MAP {
    tag "$sample"
    cpus 6
    memory '4 GB'
    publishDir "${params.outdir}/mapping", mode: 'copy'

    input:
    tuple val(sample), path(r1), path(r2)
    path index_dir

    output:
    tuple val(sample), path("${sample}.sorted.bam"), path("${sample}.sorted.bam.bai"), emit: bam
    path("${sample}.flagstat.txt"), emit: flagstat
    path("${sample}.samtools_stats.txt"), emit: stats
    path("${sample}.bwa.log"), emit: log

    script:
    """
    bwa mem -t ${task.cpus} \\
        -R '@RG\\tID:${sample}\\tSM:${sample}\\tPL:ILLUMINA' \\
        ${index_dir}/reference.fasta ${r1} ${r2} 2> ${sample}.bwa.log \\
        | samtools sort -@ 2 -m 1G -o ${sample}.sorted.bam -
    samtools index ${sample}.sorted.bam
    samtools flagstat ${sample}.sorted.bam > ${sample}.flagstat.txt
    samtools stats ${sample}.sorted.bam > ${sample}.samtools_stats.txt
    """
}

process CIRCULAR_CONSENSUS {
    tag "$sample"
    cpus 2
    memory '4 GB'
    publishDir "${params.outdir}/consensus", mode: 'copy'

    input:
    tuple val(sample), path(bam), path(bai), path(vr_consensus)
    path reference

    output:
    tuple val(sample),
        path("${sample}.consensus.fasta"),
        path("${sample}.depth.tsv"),
        path("${sample}.coverage.tsv"),
        path("${sample}.consensus_stats.tsv"),
        path("${sample}.boundary_patch.tsv"),
        path("${sample}.circular.consensus.fasta"), emit: results

    script:
    """
    python ${params.script_dir}/circular_consensus.py \\
        --bam ${bam} \\
        --reference ${reference} \\
        --sample ${sample} \\
        --outdir . \\
        --viralrecon-consensus ${vr_consensus}
    """
}

process COMPARATIVE_MAFFT {
    cpus 4
    memory '4 GB'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'comparative/**'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'alignment/**'

    input:
    path consensus_files
    path coverage_files
    path public_fasta
    path public_metadata
    path sample_metadata

    output:
    path 'comparative/all_hbv_sequences.fasta', emit: sequences
    path 'comparative/all_hbv_metadata.tsv', emit: metadata
    path 'comparative/comparative_checks.txt', emit: checks
    path 'alignment/hbv_alignment.fasta', emit: alignment
    path 'alignment/alignment_stats.txt', emit: alignment_stats
    path 'alignment/alignment_stats.tsv', emit: alignment_stats_tsv
    path 'alignment/per_sequence_stats.tsv', emit: per_sequence
    path 'alignment/variable_sites.tsv', emit: variable_sites

    script:
    """
    mkdir -p consensus coverage comparative alignment
    cp ${consensus_files} consensus/
    cp ${coverage_files} coverage/
    python ${params.script_dir}/combine_comparative.py \\
        --public-fasta ${public_fasta} \\
        --public-metadata ${public_metadata} \\
        --consensus-dir consensus \\
        --coverage-dir coverage \\
        --sample-metadata ${sample_metadata} \\
        --outdir comparative
    mafft --auto --reorder --thread ${task.cpus} \\
        comparative/all_hbv_sequences.fasta > alignment/hbv_alignment.fasta
    python ${params.script_dir}/alignment_stats.py \\
        --alignment alignment/hbv_alignment.fasta --outdir alignment
    """
}

process PHYLOGENY {
    cpus 4
    memory '4 GB'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'phylogeny'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'recombination'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'hbv_phylogeny.*'

    input:
    path alignment

    output:
    path 'phylogeny', emit: phylogeny
    path 'recombination', emit: recombination
    path 'hbv_phylogeny.treefile', emit: treefile
    path 'hbv_phylogeny.iqtree', emit: report
    path 'hbv_phylogeny.log', emit: log

    script:
    """
    mkdir -p phylogeny/S phylogeny/P recombination alignment/regions
    iqtree2 -s ${alignment} -m MFP -B 1000 --alrt 1000 -nt AUTO \\
        --prefix phylogeny/hbv_phylogeny -redo > phylogeny/iqtree.stdout.log
    python ${params.script_dir}/root_tree.py \\
        --tree phylogeny/hbv_phylogeny.treefile \\
        --out phylogeny/hbv_phylogeny.rooted.treefile
    python ${params.script_dir}/extract_alignment_regions.py \\
        --alignment ${alignment} --outdir alignment/regions
    for region in S P; do
        iqtree2 -s alignment/regions/hbv_\${region}.fasta -m MFP -B 1000 --alrt 1000 -nt AUTO \\
            --prefix phylogeny/\${region}/hbv_\${region} -redo > phylogeny/\${region}/iqtree.stdout.log
        python ${params.script_dir}/root_tree.py \\
            --tree phylogeny/\${region}/hbv_\${region}.treefile \\
            --out phylogeny/\${region}/hbv_\${region}.rooted.treefile
    done
    Phi -f ${alignment} -t D -p 1000 -o -v > recombination/phipack.txt
    cp phylogeny/hbv_phylogeny.treefile hbv_phylogeny.treefile
    cp phylogeny/hbv_phylogeny.iqtree hbv_phylogeny.iqtree
    cp phylogeny/hbv_phylogeny.log hbv_phylogeny.log
    """
}

process ANNOTATE {
    cpus 2
    memory '4 GB'
    publishDir "${params.outdir}", mode: 'copy', pattern: 'variants'

    input:
    path consensus_files
    path depth_files
    path public_fasta
    path public_metadata
    path sample_metadata
    path reference_genbank

    output:
    path 'variants', emit: variants

    script:
    """
    echo "HBV variant annotation v2"
    mkdir -p consensus variants
    cp ${consensus_files} consensus/
    cp ${depth_files} consensus/
    python ${params.script_dir}/annotate_variants.py \\
        --reference-genbank ${reference_genbank} \\
        --public-fasta ${public_fasta} \\
        --public-metadata ${public_metadata} \\
        --consensus-dir consensus \\
        --depth-dir consensus \\
        --sample-metadata ${sample_metadata} \\
        --outdir variants
    """
}

process FIGURES_REPORT {
    cpus 2
    memory '4 GB'
    publishDir "${params.outdir}", mode: 'copy'

    input:
    path treefile
    path variants_dir
    path consensus_dir

    output:
    path 'figures', emit: figures
    path 'genome_coverage.png', emit: coverage_png
    path 'phylogenetic_tree.png', emit: tree_png
    path 'mutation_summary.png', emit: mutation_png
    path 'hbv_genome_structure.png', emit: genome_png
    path 'analysis_summary.html', emit: summary
    path 'variants/mutation_summary.html', emit: mutation_html

    script:
    """
    python ${params.script_dir}/combine_mapping_stats.py \\
        --mapping-dir ${params.outdir}/mapping \\
        --consensus-dir ${params.outdir}/consensus \\
        --viralrecon-dir ${params.viralrecon_dir} \\
        --samples ${params.sample_metadata}
    python ${params.script_dir}/make_figures.py \\
        --results ${params.outdir} \\
        --metadata ${params.outdir}/comparative/all_hbv_metadata.tsv \\
        --tree ${params.outdir}/phylogeny/hbv_phylogeny.rooted.treefile \\
        --outdir ${params.outdir}/figures
    python ${params.script_dir}/make_report.py --results ${params.outdir}
    mkdir -p figures variants
    cp ${params.outdir}/figures/*.png figures/ 2>/dev/null || true
    cp ${params.outdir}/figures/genome_coverage.png .
    cp ${params.outdir}/figures/phylogenetic_tree.png .
    cp ${params.outdir}/figures/mutation_summary.png .
    cp ${params.outdir}/figures/hbv_genome_structure.png .
    cp ${params.outdir}/analysis_summary.html analysis_summary.html
    cp ${params.outdir}/variants/mutation_summary.html variants/mutation_summary.html
    """
}

workflow {
    samples = Channel.fromPath(params.input)
        .splitCsv(header: true)
        .map { row -> tuple(row.sample, file(row.fastq_1), file(row.fastq_2)) }

    viralrecon_consensus = Channel.fromPath(
            "${params.viralrecon_dir}/variants/bcftools/consensus/bcftools/*.consensus.fa"
        )
        .map { file -> tuple(file.name.replace('.consensus.fa', ''), file) }

    FASTP(samples)
    BWA_INDEX(Channel.value(file(params.extended_reference)))
    BWA_MAP(FASTP.out.reads, BWA_INDEX.out.index)

    bam_with_viralrecon = BWA_MAP.out.bam.join(viralrecon_consensus, by: 0)
    CIRCULAR_CONSENSUS(
        bam_with_viralrecon,
        Channel.value(file(params.reference))
    )

    consensus_files = CIRCULAR_CONSENSUS.out.results.map { it[1] }.collect()
    coverage_files  = CIRCULAR_CONSENSUS.out.results.map { it[3] }.collect()
    depth_files     = CIRCULAR_CONSENSUS.out.results.map { it[2] }.collect()

    COMPARATIVE_MAFFT(
        consensus_files,
        coverage_files,
        Channel.value(file(params.public_fasta)),
        Channel.value(file(params.public_metadata)),
        Channel.value(file(params.sample_metadata))
    )

    PHYLOGENY(COMPARATIVE_MAFFT.out.alignment)

    ANNOTATE(
        consensus_files,
        depth_files,
        Channel.value(file(params.public_fasta)),
        Channel.value(file(params.public_metadata)),
        Channel.value(file(params.sample_metadata)),
        Channel.value(file("${launchDir}/references/genbank/NC_003977.2.gb"))
    )

    FIGURES_REPORT(
        PHYLOGENY.out.treefile,
        ANNOTATE.out.variants,
        CIRCULAR_CONSENSUS.out.results.map { it[1] }.collect()
    )
}
