#!/bin/bash
# Installs the dungeonOS theme for Signal Desktop (asks for your password).
#
#   ~/Dotfiles/signal/install.sh            theme Signal, and re-theme it after every update
#   ~/Dotfiles/signal/install.sh --restore  remove the theme and the update hook
#
# The patcher and theme are copied to /usr/local/share/dungeonOS/signal, and a pacman hook
# reruns them whenever signal-desktop is installed or updated (an update replaces the
# themed files with plain ones).

set -euo pipefail
HERE="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
SHARE=/usr/local/share/dungeonOS/signal
HOOK=/etc/pacman.d/hooks/signal-dungeonOS.hook

[ "$EUID" -eq 0 ] || exec sudo "$0" "$@"

if [ "${1:-}" = "--restore" ]; then
    python3 "$HERE/patch.py" --restore
    rm -f "$HOOK"
    rm -rf "$SHARE"
    echo "Theme and update hook removed. Restart Signal."
    exit 0
fi

mkdir -p "$SHARE" "$(dirname "$HOOK")"
install -m 644 "$HERE/patch.py" "$HERE/dungeonOS.css" "$SHARE/"
cat > "$HOOK" <<HOOKEOF
# written by ~/Dotfiles/signal/install.sh
[Trigger]
Operation = Install
Operation = Upgrade
Type = Package
Target = signal-desktop

[Action]
Description = Applying the dungeonOS theme to Signal...
When = PostTransaction
Exec = /usr/bin/python3 $SHARE/patch.py
HOOKEOF
echo "update hook -> $HOOK"
python3 "$SHARE/patch.py"
