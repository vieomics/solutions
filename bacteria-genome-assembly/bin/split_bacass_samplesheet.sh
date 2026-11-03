#!/usr/bin/env bash
# Split a combined nf-core/bacass samplesheet into one TSV per sample.
#
# Usage:
#   bin/split_bacass_samplesheet.sh \
#     --input bacass_samplesheet.tsv \
#     --outdir samplesheets/local \
#     --sample-regex 'ERR[0-9]+'
#
# By default the output file is named after the `ID` column. If
# `--sample-regex` is given, the first match anywhere in the row is used
# instead. That is useful when `ID` is an ENA experiment accession (`ERX...`)
# but the run accession (`ERR...`) is what you want in file and job names.
set -euo pipefail

INPUT=""
OUTDIR="samplesheets/local"
SAMPLE_REGEX=""

usage() {
    sed -n '2,14p' "$0" | sed 's/^# \{0,1\}//'
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --input | -i)
            INPUT="${2:?--input needs a value}"
            shift 2
            ;;
        --outdir | -o)
            OUTDIR="${2:?--outdir needs a value}"
            shift 2
            ;;
        --sample-regex | -r)
            SAMPLE_REGEX="${2:?--sample-regex needs a value}"
            shift 2
            ;;
        -h | --help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [ -z "$INPUT" ]; then
    echo "Missing --input <samplesheet.tsv>" >&2
    exit 2
fi
if [ ! -f "$INPUT" ]; then
    echo "No such samplesheet: $INPUT" >&2
    exit 1
fi

mkdir -p "$OUTDIR"

awk -F'\t' -v outdir="$OUTDIR" -v regex="$SAMPLE_REGEX" '
NR == 1 {
    header = $0
    next
}
{
    sample = $1
    if (regex != "" && match($0, regex)) {
        sample = substr($0, RSTART, RLENGTH)
    }
    if (sample == "") {
        print "Empty sample name on line " NR > "/dev/stderr"
        exit 1
    }
    file = outdir "/" sample ".tsv"
    if (!(sample in seen)) {
        print header > file
        seen[sample] = 1
    }
    print $0 >> file
    count[sample]++
}
END {
    for (sample in count) {
        print sample " (" count[sample] " row(s))" > "/dev/stderr"
    }
}
' "$INPUT"

echo "Wrote one-row samplesheets to $OUTDIR" >&2
