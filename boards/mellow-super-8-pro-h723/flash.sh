#!/bin/bash
MCU=/dev/mellow-super-8-pro-h723
if [ "$EUID" -ne 0 ]
  then echo "ERROR: Please run as root"
  exit
fi
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
FLASH_SCRIPT=$(realpath "$SCRIPT_DIR/../../scripts/flash-path.sh")
$FLASH_SCRIPT $MCU
