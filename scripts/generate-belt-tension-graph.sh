#!/bin/bash
set -e -u
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh

## the TEST_RESONANCES command seems to return before all data is completely
## written. it'd be better to poll for the files to be completely written,
## but this has been reliable for me so far…
sleep 10

outdir="${SCRIPT_DIR}"/../../input_shaper
if [ ! -d "${outdir}" ]; then
    mkdir "${outdir}"
    chown ${RATOS_USERNAME}:${RATOS_USERGROUP} "$SCRIPT_DIR"/../../input_shaper
fi

NEWUPPER=$(find /tmp -name "raw_data_axis*_belt-tension-upper.csv" -printf '%T@ %p\n' 2> /dev/null | sort -n | tail -1 | cut -f2- -d" ")
NEWLOWER=$(find /tmp -name "raw_data_axis*_belt-tension-lower.csv" -printf '%T@ %p\n' 2> /dev/null | sort -n | tail -1 | cut -f2- -d" ")

${KLIPPER_DIR}/scripts/graph_accelerometer.py \
    -c "$NEWLOWER" "$NEWUPPER" \
    -o "${outdir}/belt-tension-resonances-$( date +'%Y-%m-%d-%H%M%S' ).png"
