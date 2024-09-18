#!/bin/bash

# shellcheck source=./scripts/ratos-common.sh
source "$SCRIPT_DIR"/ratos-common.sh

MCU=$1
if [ "$EUID" -ne 0 ]
  then echo "ERROR: Please run as root"
  exit 1
fi
if [ "$MCU" == "" ]; then
	echo "ERROR: Please specify a device to flash"
	exit 1
fi
pushd ${KLIPPER_DIR} || exit
service klipper stop
dfuDevicesPreFlash=$(lsusb | grep -c "0483:df11")
if [ -h "$MCU" ]; then
    echo "Flashing $MCU"
    sudo make flash FLASH_DEVICE="$MCU"
fi
sleep 5
retVal=1
if [ -h "$MCU" ]; then
	retVal=0
else
	dfuDevicesPostFlash=$(lsusb | grep -c "0483:df11")
	if [ "$dfuDevicesPreFlash" -eq 0 ] && [ "$dfuDevicesPostFlash" -eq 1 ]; then
		echo "Seems like flashing failed, but the device is still in DFU mode. Attempting to recover."
		make flash FLASH_DEVICE=0483:df11
		sleep 5
		if [ -h "$MCU" ]; then
			retVal=0
		fi
	fi
fi
if [ $retVal -eq 0 ]; then
	echo "Flashing successful."
else
	echo "Flashing failed."
fi
chown ${RATOS_USERNAME}:${RATOS_USERGROUP} -R ${KLIPPER_DIR}
service klipper start
popd || exit
exit $retVal
