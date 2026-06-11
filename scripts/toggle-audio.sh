#!/bin/bash

USB=$(wpctl status | grep 'Fosi Audio SK02 Analog' | grep 'vol:' | grep -oP '\d+(?=\.)' | head -1)
BT=$(wpctl status | grep 'SoundCore 2' | grep 'vol:' | grep -oP '\d+(?=\.)' | head -1)
CURRENT=$(wpctl status | grep -A20 'Sinks:' | grep '\*' | head -1 | grep -oP '\d+(?=\.)' | head -1)

if [ "$CURRENT" = "$USB" ]; then
    TARGET=$BT
    NAME="SoundCore 2"
else
    TARGET=$USB
    NAME="Fosi Audio SK02"
fi

wpctl set-default "$TARGET"
echo "Switched to $NAME"
