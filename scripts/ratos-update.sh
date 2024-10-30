#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "ERROR: Please run as root"
  exit
fi

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh
# shellcheck source=./scripts/moonraker-ensure-policykit-rules.sh
source "$SCRIPT_DIR"/moonraker-ensure-policykit-rules.sh

update_symlinks()
{
  echo "Updating RatOS device symlinks.."
  rm /etc/udev/rules.d/98-*.rules
  ln -s /home/pi/printer_data/config/RatOS/boards/*/*.rules /etc/udev/rules.d/
}

ensure_node_18()
{
	node -v | grep "^v18" > /dev/null
	isinstalled=$?
	if [ $isinstalled -eq 0 ]
	then
		echo "Node 18 already installed"
	else
		echo "Installing Node 18"
		sed -i 's/node_16\.x/node_18\.x/g' /etc/apt/sources.list.d/nodesource.list
		apt-get update
		apt-get install -y nodejs
	fi
}

fix_klippy_env_ownership()
{
	if [ -n "$(find /home/pi/klippy-env/lib/python3.9/site-packages/matplotlib -user "root" -print -prune -o -prune)" ]; then
		chown -R pi:pi /home/pi/klippy-env
	fi
}

restart_configurator()
{
	report_status "Restarting configurator..."
	systemctl restart ratos-configurator
}

symlink_extensions()
{
	report_status "Symlinking klippy extensions"
	ratos extensions symlink
	configurator_success=$?
	if [ ! $configurator_success -eq 0 ]
	then
		echo "Failed to symlink klippy extensions. Is the RatOS configurator running?"
		exit 1
	fi
}

# Run update symlinks
update_symlinks
ensure_sudo_command_whitelisting root
ensure_service_permission
fix_klippy_env_ownership
install_beacon
install_hooks
ensure_node_18
patch_klipperscreen_service_restarts
register_z_offset_probe
remove_old_postprocessor
register_ratos
register_resonance_generator
register_ratos_kinematics
unregister_vaoc_led
symlink_extensions
update_beacon_fw
restart_configurator
