#!/bin/bash
# CPU temperature for waybar. Tries the usual sensors so it works on any machine:
# k10temp/zenpower (AMD), coretemp (Intel), cpu_thermal (ARM), then the ACPI zone.
for name in k10temp zenpower coretemp cpu_thermal acpitz; do
    HWMON=$(grep -lx "$name" /sys/class/hwmon/*/name 2>/dev/null | head -1 | xargs -r dirname)
    if [ -n "$HWMON" ] && [ -r "$HWMON/temp1_input" ]; then
        echo "$(( $(cat "$HWMON/temp1_input") / 1000 ))°C"
        exit 0
    fi
done
# no sensor found: print nothing, and waybar hides the module
