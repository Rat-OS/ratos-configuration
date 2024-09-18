#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh

NEWY=$(find /tmp -name "resonances_y_*.csv" -printf '%T@ %p\n' 2> /dev/null | sort -n | tail -1 | cut -f2- -d" ")
DATE=$(date +'%Y-%m-%d-%H%M%S')
if [ ! -d "$SCRIPT_DIR/../../input_shaper" ]
then
    mkdir "$SCRIPT_DIR"/../../input_shaper
    chown ${RATOS_USERNAME}:${RATOS_USERGROUP} "$SCRIPT_DIR"/../../input_shaper
fi

${KLIPPER_DIR}/scripts/calibrate_shaper.py "$NEWY" -o "$SCRIPT_DIR"/../../input_shaper/resonances_y_"$DATE".png
