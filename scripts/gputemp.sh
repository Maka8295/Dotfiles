#!/bin/bash
# GPU temperature for waybar: AMD (amdgpu, "edge" sensor) or NVIDIA (nvidia-smi).
# Integrated laptop graphics usually have no sensor of their own; then this prints
# nothing and waybar hides the module. Prints JSON with a heat class (temp-json.sh,
# shared with cputemp.sh).
source "$(dirname "$0")/temp-json.sh"
HWMON=$(grep -lx amdgpu /sys/class/hwmon/*/name 2>/dev/null | head -1 | xargs -r dirname)
if [ -n "$HWMON" ] && [ -r "$HWMON/temp1_input" ]; then
    temp_json $(( $(cat "$HWMON/temp1_input") / 1000 ))
elif command -v nvidia-smi >/dev/null; then
    T=$(nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader,nounits 2>/dev/null | head -1)
    [ -n "$T" ] && temp_json "$T"
fi
