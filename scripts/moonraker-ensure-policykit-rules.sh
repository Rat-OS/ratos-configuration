#!/bin/bash

# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh

POLKIT_LEGACY_DIR="/etc/polkit-1/localauthority/50-local.d"
POLKIT_DIR="/etc/polkit-1/rules.d"
POLKIT_USR_DIR="/usr/share/polkit-1/rules.d"

ensure_moonraker_policiykit_rules() {
	if [[ -e ${POLKIT_USR_DIR}/moonraker.rules ]]
	then
		echo -e "\n\n###### Moonraker policy exists, skipping policykit script."
		return
	fi
	if [[ -e ${POLKIT_DIR}/moonraker.rules ]]
	then
		echo -e "\n\n###### Moonraker policy exists, skipping policykit script."
		return
	fi
	if [[ -e ${POLKIT_LEGACY_DIR}/10-moonraker.pkla ]]
	then
		echo -e "\n\n###### Moonraker legacy policy exists, skipping policykit script."
		return
	fi
	if [[ -e ${MOONRAKER_DIR}/scripts/set-policykit-rules.sh ]]
	then
		cp ${MOONRAKER_DIR}/scripts/set-policykit-rules.sh /tmp/set-policykit-rules.sh
		# if moonraker restarts the update process will be terminated, leaving a broken moonraker install.
		sed -i 's/sudo systemctl restart moonraker/#sudo systemctl restart moonraker/g' /tmp/set-policykit-rules.sh
		#sed -i ':a;N;$!ba;s/verify_ready\n/#verify_ready\n/g' /tmp/set-policykit-rules.sh
		echo -e "\n\n###### Moonraker policy not found, running moonraker policykit script..."
		if [ "$EUID" -eq 0 ]; then
			# This feels wrong, but...
			OLDUSER=$USER
			USER=${RATOS_USERNAME}
			/tmp/set-policykit-rules.sh --root
			USER=$OLDUSER
		else
			/tmp/set-policykit-rules.sh
		fi
		return 1
	fi
}
