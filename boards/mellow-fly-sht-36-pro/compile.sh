#!/bin/bash
if [ "$EUID" -ne 0 ]
  then echo "ERROR: Please run as root"
  exit
fi
cp -f /home/pi/printer_data/config/RatOS/boards/mellow-fly-sht-36-pro/firmware.config /home/pi/klipper/.config
pushd /home/pi/klipper || exit
make olddefconfig
make clean
make

if [ ! -d "/home/pi/printer_data/config/firmware_binaries" ]
then
    mkdir /home/pi/printer_data/config/firmware_binaries
    chown pi:pi /home/pi/printer_data/config/firmware_binaries
fi
cp -f /home/pi/klipper/out/klipper.bin /home/pi/printer_data/config/firmware_binaries/firmware-mellow-fly-sht-36-pro.bin
chown pi:pi /home/pi/printer_data/config/firmware_binaries/firmware-mellow-fly-sht-36-pro.bin
popd || exit
