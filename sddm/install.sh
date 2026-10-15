#!/bin/bash
# Installs the dungeonOS login screen (SDDM theme) system-wide.
#
#   ~/Dotfiles/sddm/install.sh            install (asks for your password)
#   ~/Dotfiles/sddm/install.sh --preview  try it in a window, no install, no password
#
# The login screen runs as the "sddm" user, which can't read your home folder, so the
# theme, its fonts, the wallpaper and the cursor theme are copied into system folders.

set -euo pipefail
HERE="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
DOT="$(dirname "$HERE")"

# full theme folder = the QML in dungeonOS/ + wallpaper + fonts
stage() {
    local dest="$1"
    rm -rf "$dest"
    cp -r "$HERE/dungeonOS" "$dest"
    cp "$DOT/wallpapers/cambridge.jpg" "$dest/background.jpg"
    mkdir -p "$dest/fonts"
    cp "$DOT/fonts/CloisterBlack.ttf" "$dest/fonts/"
}

if [ "${1:-}" = "--preview" ]; then
    tmp="$(mktemp -d)/dungeonOS"
    stage "$tmp"
    exec sddm-greeter-qt6 --test-mode --theme "$tmp"
fi

[ "$EUID" -eq 0 ] || exec sudo "$0" "$@"

stage /usr/share/sddm/themes/dungeonOS
echo "theme   -> /usr/share/sddm/themes/dungeonOS"

# cursor theme (self-contained, so a plain copy works)
rm -rf /usr/share/icons/dungeonOS-cursor
cp -r "$DOT/cursor/dungeonOS-cursor" /usr/share/icons/
echo "cursor  -> /usr/share/icons/dungeonOS-cursor"

mkdir -p /etc/sddm.conf.d
cat > /etc/sddm.conf.d/dungeonOS.conf <<CONF
# written by ~/Dotfiles/sddm/install.sh
[Theme]
Current=dungeonOS
CursorTheme=dungeonOS-cursor
CursorSize=64
CONF
echo "config  -> /etc/sddm.conf.d/dungeonOS.conf"
echo "Done. You'll see it the next time you log out or reboot."
