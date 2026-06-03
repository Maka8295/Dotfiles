#!/bin/bash
USB=65
BT=95

CURRENT=$(wpctl status | grep -A20 'Sinks:' | grep '\*' | head -1 | grep -oP '(?<=\*\s{3})\d+')

if [ "$CURRENT" = "$USB" ]; then
    TARGET=$BT
    NAME="SoundCore 2"
else
    TARGET=$USB
    NAME="Fosi Audio SK02"
fi

wpctl set-default "$TARGET"
echo "Switched to $NAME"
