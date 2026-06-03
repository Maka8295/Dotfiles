#!/bin/bash
HWMON=$(grep -rl 'k10temp' /sys/class/hwmon/*/name | head -1 | xargs dirname)
TEMP=$(cat "$HWMON/temp1_input")
echo "$((TEMP / 1000))°C"
