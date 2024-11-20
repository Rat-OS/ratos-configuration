#!/bin/sh
logfile="/var/log/ratos.log"
moonraker="http://localhost:7125/"
printer="/home/pi/printer_data/comms/klippy.serial"

touch "$logfile"
chmod 664 "$logfile"

echo "$(date +"%Y-%m-%d %T"): MCU Detected" >> "$logfile"

# Query moonraker to get printer state
state=$(curl ${moonraker%/}/printer/info | \
    python3 -c "import sys, json; print(json.load(sys.stdin)['result']['state'])")
echo State is \"${state}\"

# If [ -h $printer] is true but [ -e $printer is false ] $printer is probably
# a symbolic link in a directory with the sticky bit set, or one of the links
# in a chain of symlinks is in a directory with the sticky bit set.
# In this case, it will not be possible to write to $printer if that symlink
# it is owned by a different user. /tmp often has the sticky bit set. 
#
# Dereference and keep dereferencing until $printer points to a file or 
# symlink to which the RESTART command can actually be written

while [ ! -e $printer ] && [ -h $printer ]
do
    printer=$(readlink $printer)
done

# Only proceed if state reported by moonraker is "shutdown"

if [ -z "$state" ]; then 
    echo "$(date +"%Y-%m-%d %T"): Error querying ${moonraker} or parsing response ${state}." >> "$logfile"

elif [ ${state} = shutdown ] || [ ${state} = error ]; then

    if [ -e $printer ]; then
        echo "RESTART" > $printer
        echo "$(date +"%Y-%m-%d %T"): RESTART command sent to $printer" >> "$logfile"
    else
        echo "$(date +"%Y-%m-%d %T"): $printer does not exist" >> "$logfile"
    fi
else
    echo "$(date +"%Y-%m-%d %T"): Moonraker reported printer status of \"${state}\". Ignoring MCU detect event." >> "$logfile"
fi
