#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
report_status()
{
    echo -e "\n\n###### $1"
}

disable_modem_manager()
{
	report_status "Checking if ModemManager is enabled..."
	
	if ! sudo systemctl is-enabled ModemManager.service &> /dev/null; then
		report_status "Disabling ModemManager..."
		sudo systemctl disable ModemManager.service
	else
		report_status "ModemManager is already disabled.."
	fi
	report_status "Masking ModemManager to ensure it won't start in the future..."
	sudo systemctl mask ModemManager.service
}

update_beacon_fw()
{
	report_status "Updating beacon firmware..."
	KLIPPER_DIR="/home/pi/klipper"
	KLIPPER_ENV="/home/pi/klippy-env"
	BEACON_DIR="/home/pi/beacon"
	if [ ! -d "$BEACON_DIR" ] || [ ! -e "$KLIPPER_DIR/klippy/extras/beacon.py" ]; then
		echo "beacon: beacon isn't installed, skipping..."
		return
	fi

	if [ ! -d "$KLIPPER_DIR" ] || [ ! -d "$KLIPPER_ENV" ]; then
		echo "beacon: klipper or klippy env doesn't exist"
		return
	fi

	if [ ! -f "$BEACON_DIR/update_firmware.py" ]; then
		echo "beacon: beacon firmware updater script doesn't exist, skipping..."
		return
	fi
	$KLIPPER_ENV/bin/python $BEACON_DIR/update_firmware.py update all --no-sudo
}

install_beacon()
{
	KLIPPER_DIR="/home/pi/klipper"
	KLIPPER_ENV="/home/pi/klippy-env"
	BEACON_DIR="/home/pi/beacon"
    report_status "Installing beacon module..."

	if [ -d "$BEACON_DIR" ] || [ -e "$KLIPPER_DIR/klippy/extras/beacon.py" ]; then
		echo "beacon: beacon already installed, skipping..."
		return
	fi

	if [ ! -d "$KLIPPER_DIR" ] || [ ! -d "$KLIPPER_ENV" ]; then
		echo "beacon: klipper or klippy env doesn't exist"
		return
	fi

	pushd "/home/pi" || return
	git clone https://github.com/beacon3d/beacon_klipper.git beacon
	chown -R pi:pi beacon
	popd || return

	# install beacon requirements to env
	echo "beacon: installing python requirements to env."
	"${KLIPPER_ENV}/bin/pip" install -r "${BEACON_DIR}/requirements.txt"

	# update link to beacon.py
	echo "beacon: registering beacon with the configurator."
	_register_klippy_extension "beacon" "$BEACON_DIR" "beacon.py"

}

_register_klippy_extension() {
	EXT_NAME=$1
    EXT_PATH=$2
    EXT_FILE=$3
	ERROR_IF_EXISTS=$4
	[[ "$ERROR_IF_EXISTS" == "false" ]] && ERROR_IF_EXISTS="" || ERROR_IF_EXISTS="-e "

    report_status "Registering klippy extension '$EXT_NAME' with the RatOS Configurator..."
    if [ ! -e "$EXT_PATH/$EXT_FILE" ]
    then
        echo "ERROR: The file you're trying to register does not exist"
        exit 1
    fi

    # shellcheck disable=SC2086
    if ! ratos extensions register klipper $ERROR_IF_EXISTS"$EXT_NAME" "$EXT_PATH"/"$EXT_FILE"
    then
        echo "ERROR: Failed to register $EXT_NAME. Is the RatOS configurator running?"
        exit 1
    fi
}

regenerate_config() {
    report_status "Regenerating RatOS configuration via RatOS Configurator..."

    ratos config regenerate
}

register_gcode_shell_command()
{
    EXT_NAME="gcode_shell_extension"
    EXT_PATH=$(realpath "$SCRIPT_DIR"/../klippy)
    EXT_FILE="gcode_shell_command.py"
    _register_klippy_extension $EXT_NAME "$EXT_PATH" $EXT_FILE
}

register_ratos_homing()
{
    EXT_NAME="ratos_homing_extension"
    EXT_PATH=$(realpath "$SCRIPT_DIR"/../klippy)
    EXT_FILE="ratos_homing.py"
	# Don't error if extension is already registered
    _register_klippy_extension $EXT_NAME "$EXT_PATH" $EXT_FILE "false"
}

register_resonance_generator()
{
    EXT_NAME="resonance_generator_extension"
    EXT_PATH=$(realpath "$SCRIPT_DIR"/../klippy)
    EXT_FILE="resonance_generator.py"
	# Don't error if extension is already registered
    _register_klippy_extension $EXT_NAME "$EXT_PATH" $EXT_FILE "false"
}

unregister_vaoc_led()
{
	if ratos extensions list | grep "vaoc_led" &>/dev/null; then
		report_status "Unregistering experimental vaoc_led extension..."
		ratos extensions unregister klipper vaoc_led
	fi
}

register_z_offset_probe()
{
    EXT_NAME="z_offset_probe_extension"
    EXT_PATH=$(realpath "$SCRIPT_DIR"/../klippy)
    EXT_FILE="z_offset_probe.py"
	# Don't error if extension is already registered
    _register_klippy_extension $EXT_NAME "$EXT_PATH" $EXT_FILE "false"
}

register_ratos_kinematics() {
	if ratos extensions list | grep "ratos-kinematics" &>/dev/null; then
		ratos extensions unregister klipper -k ratos_hybrid_corexy
	fi
	if [ -e /home/pi/ratos-kinematics ]; then
		report_status "Removing old ratos-kinematics directory..."
		rm -rf /home/pi/ratos-kinematics
	fi
    EXT_NAME="ratos_hybrid_corexy"
    EXT_PATH=$(realpath "${SCRIPT_DIR}/../klippy/kinematics/ratos_hybrid_corexy.py")
    ratos extensions register klipper -k $EXT_NAME "$EXT_PATH"
}

register_ratos()
{
    EXT_NAME="ratos_extension"
    EXT_PATH=$(realpath "$SCRIPT_DIR"/../klippy)
    EXT_FILE="ratos.py"
	# Don't error if extension is already registered
    _register_klippy_extension $EXT_NAME "$EXT_PATH" $EXT_FILE "false"
}

remove_old_postprocessor()
{
	if [ -L /home/pi/klipper/klippy/extras/ratos_post_processor.py ]; then
		report_status "Removing old postprocessor.py..."
		rm /home/pi/klipper/klippy/extras/ratos_post_processor.py
	fi
}

install_hooks()
{
    report_status "Installing git hooks"
	if [[ ! -L /home/pi/printer_data/config/RatOS/.git/hooks/post-merge ]]
	then
 	   ln -s "$SCRIPT_DIR"/ratos-post-merge.sh "$SCRIPT_DIR"/../.git/hooks/post-merge
	fi
	if [[ ! -L /home/pi/klipper/.git/hooks/post-merge ]]
	then
 	   ln -s "$SCRIPT_DIR"/klipper-post-merge.sh /home/pi/klipper/.git/hooks/post-merge
	fi
	if [[ ! -L /home/pi/moonraker/.git/hooks/post-merge ]]
	then
 	   ln -s "$SCRIPT_DIR"/moonraker-post-merge.sh /home/pi/moonraker/.git/hooks/post-merge
	fi
	if [[ ! -L /home/pi/beacon/.git/hooks/post-merge ]]
	then
 	   ln -s "$SCRIPT_DIR"/beacon-post-merge.sh /home/pi/beacon/.git/hooks/post-merge
	fi
}

ensure_service_permission()
{
	report_status "Updating service permissions"
	if ! grep "klipper_mcu" /home/pi/printer_data/moonraker.asvc &>/dev/null || ! grep "ratos-configurator" /home/pi/printer_data/moonraker.asvc &>/dev/null; then
		cat << '#EOF' > /home/pi/printer_data/moonraker.asvc
klipper_mcu
webcamd
MoonCord
KlipperScreen
moonraker-telegram-bot
moonraker-obico
sonar
crowsnest
octoeverywhere
ratos-configurator
#EOF

		report_status "Configurator added to moonraker service permissions"
	fi
}

patch_klipperscreen_service_restarts()
{
	if grep "StartLimitIntervalSec=0" /etc/systemd/system/klipperscreen.service &>/dev/null; then
		report_status "Patching KlipperScreen service restarts..."
		# Fix restarts
		sudo sed -i 's/\RestartSec=1/\RestartSec=5/g' /etc/systemd/system/KlipperScreen.service
		sudo sed -i 's/\StartLimitIntervalSec=0/\StartLimitIntervalSec=100\nStartLimitBurst=4/g' /etc/systemd/system/KlipperScreen.service
		sudo systemctl daemon-reload
		report_status "KlipperScreen service patched"
	fi
}

ensure_sudo_command_whitelisting()
{
	sudo="sudo"
	if [ "$1" = "root" ]
	then
		sudo=""
	fi
    report_status "Updating whitelisted commands"
	# Whitelist RatOS git hook scripts
	if [[ -e /etc/sudoers.d/030-ratos-githooks ]]
	then
		$sudo rm /etc/sudoers.d/030-ratos-githooks
	fi
	touch /tmp/030-ratos-githooks
	cat << '#EOF' > /tmp/030-ratos-githooks
pi  ALL=(ALL) NOPASSWD: /home/pi/printer_data/config/RatOS/scripts/ratos-update.sh
pi  ALL=(ALL) NOPASSWD: /home/pi/printer_data/config/RatOS/scripts/klipper-mcu-update.sh
pi  ALL=(ALL) NOPASSWD: /home/pi/printer_data/config/RatOS/scripts/beacon-update.sh
pi  ALL=(ALL) NOPASSWD: /home/pi/printer_data/config/RatOS/scripts/moonraker-update.sh
#EOF

	$sudo chown root:root /tmp/030-ratos-githooks
	$sudo chmod 440 /tmp/030-ratos-githooks
	$sudo cp --preserve=mode /tmp/030-ratos-githooks /etc/sudoers.d/030-ratos-githooks
}

