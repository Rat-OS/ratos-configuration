#!/bin/bash
# This script install additional dependencies
# for RatOS.

PKGLIST="python3-numpy python3-matplotlib curl"

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh

install_dependencies()
{
    report_status "Installing RatOS dependencies"
    # shellcheck disable=SC2086
    sudo apt-get update && sudo apt-get install -y $PKGLIST
}

install_printer_config()
{
    report_status "Copying printer configuration"
    PRINTER_CFG="${RATOS_PRINTER_DATA_DIR}/config/printer.cfg"
    tail -n +2 ${RATOS_PRINTER_DATA_DIR}/config/RatOS/templates/initial-printer.template.cfg > $PRINTER_CFG
}

install_udev_rules()
{
    report_status "Installing udev rules"
    sudo ln -s ${RATOS_PRINTER_DATA_DIR}/config/RatOS/boards/*/*.rules /etc/udev/rules.d/
}

verify_ready()
{
    if [ "$EUID" -eq 0 ]; then
        echo "This script must not run as root"
        exit 1
    fi
}

# Force script to exit if an error occurs
set -xe

verify_ready
install_printer_config
install_udev_rules
install_beacon
install_hooks
install_dependencies
ensure_sudo_command_whitelisting sudo
register_gcode_shell_command
register_ratos_homing
register_z_offset_probe
register_ratos
register_resonance_generator
register_ratos_kinematics
