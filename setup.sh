#!/bin/bash
# Sets up these dotfiles on a fresh Arch / CachyOS install.
#
#   ./setup.sh                 install packages, link everything, apply settings
#   ./setup.sh --no-packages   skip package installation
#
# Safe to rerun: anything already in the way (that isn't one of our links) is
# moved to <name>.bak-<timestamp> instead of being overwritten.

set -uo pipefail

DOTFILES="$(cd "$(dirname "$(realpath "$0")")" && pwd)"
CONFIG="${XDG_CONFIG_HOME:-$HOME/.config}"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
STAMP="$(date +%Y%m%d-%H%M%S)"

INSTALL_PACKAGES=1
for arg in "$@"; do
    case "$arg" in
        --no-packages) INSTALL_PACKAGES=0 ;;
        -h|--help) sed -n 2,8p "$0"; exit 0 ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

section() { printf '\n\033[1;33m== %s\033[0m\n' "$1"; }

# link <source in dotfiles> <destination>
link() {
    local src="$1" dest="$2"
    if [ ! -e "$src" ]; then
        echo "  skip  $dest (missing $src)"
        return
    fi
    mkdir -p "$(dirname "$dest")"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$src" ]; then
        echo "  ok    $dest"
        return
    fi
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        mv "$dest" "$dest.bak-$STAMP"
        echo "  saved old $dest -> $dest.bak-$STAMP"
    fi
    # -n: never follow an existing link to a directory (that is how links end up nested inside each other)
    ln -sfn "$src" "$dest"
    echo "  link  $dest -> $src"
}

# ---------------------------------------------------------------------------
section "Packages"
# ---------------------------------------------------------------------------
PACMAN_PKGS=(
    # desktop
    hyprland hyprpaper hypridle hyprlock uwsm xdg-desktop-portal-hyprland waybar rofi fuzzel grim brightnessctl wl-clipboard
    # audio
    pipewire pipewire-pulse wireplumber pavucontrol
    # apps
    kitty fish neovim btop cava cmus yazi firefox signal-desktop
    # japanese input
    fcitx5 fcitx5-mozc fcitx5-gtk fcitx5-qt fcitx5-configtool
    # fonts not kept in this repo (CJK, emoji, waybar/nvim icons)
    fontconfig noto-fonts-cjk noto-fonts-emoji ttf-nerd-fonts-symbols
    # neovim (AstroNvim) tooling
    git ripgrep fd nodejs npm python go
    # building the Hyprland border plugin
    base-devel pkgconf
)
AUR_PKGS=(neofetch grimblast-git)   # grimblast-git is in the CachyOS repo, AUR on plain Arch

if [ "$INSTALL_PACKAGES" = 1 ]; then
    # -Syu: refresh the package lists and update the system first (a fresh install
    # often has stale lists, and Arch does not support installing onto an un-updated system)
    sudo pacman -Syu --needed "${PACMAN_PKGS[@]}" || echo "  pacman failed; continuing with the rest of the setup"
    if command -v paru >/dev/null; then
        paru -S --needed "${AUR_PKGS[@]}" || echo "  paru failed; continuing"
    elif command -v yay >/dev/null; then
        yay -S --needed "${AUR_PKGS[@]}" || echo "  yay failed; continuing"
    else
        echo "  No AUR helper found; install manually: ${AUR_PKGS[*]}"
    fi
else
    echo "  skipped (--no-packages)"
fi

# ---------------------------------------------------------------------------
section "Config links"
# ---------------------------------------------------------------------------
link "$DOTFILES/bash/.bashrc"       "$HOME/.bashrc"
link "$DOTFILES/bash/.bash_profile" "$HOME/.bash_profile"

# fcitx5: started by hyprland.lua; profile = English keyboard + Japanese (mozc), Ctrl+Space toggles
for dir in btop cava cmus fcitx5 fish fuzzel hypr kicad kitty neofetch nvim rofi waybar yazi; do
    link "$DOTFILES/$dir" "$CONFIG/$dir"
done

# KiCad launchers that run it through XWayland: KiCad 10.0.7 asks wxWidgets whether a hotkey
# letter is still held down, which wxWidgets can only answer on X11 - on Wayland every hotkey
# (X, Ctrl+S, ...) pops up an "Unsupported key" assert. Made from the installed launchers,
# so they follow KiCad updates; delete ~/.local/share/applications/org.kicad.* to undo.
mkdir -p "$DATA/applications"
for desktop in /usr/share/applications/org.kicad.*.desktop; do
    [ -e "$desktop" ] || continue
    sed 's/^Exec=/Exec=env GDK_BACKEND=x11 /' "$desktop" > "$DATA/applications/$(basename "$desktop")"
    echo "  kicad launcher $(basename "$desktop") (XWayland)"
done

# Links left behind by older versions of this script whose folders no longer exist
for stale in alacritty BetterDiscord; do
    if [ -L "$CONFIG/$stale" ] && [ ! -e "$CONFIG/$stale" ] && [[ "$(readlink "$CONFIG/$stale")" == "$DOTFILES/"* ]]; then
        rm "$CONFIG/$stale"
        echo "  removed broken link $CONFIG/$stale"
    fi
done

# ---------------------------------------------------------------------------
section "Fonts"
# ---------------------------------------------------------------------------
link "$DOTFILES/fonts" "$DATA/fonts"
if command -v fc-cache >/dev/null; then
    fc-cache -f >/dev/null && echo "  font cache rebuilt"
fi

# ---------------------------------------------------------------------------
section "Cursor"
# ---------------------------------------------------------------------------
# Installed per-user, so no sudo needed. Hyprland sets it at startup (hyprland.lua);
# the settings below make GTK apps use it as well.
# dungeonOS-cursor: Final Fantasy Tactics item sprites + a pixel art gauntlet, with the
# rest recoloured from the Miku theme (kept installed as an alternative). Rebuild it with
# cursor/dungeonOS-cursor-src/build.py. Size 64 = the art scaled exactly 2x (sharp pixels).
# Linked into ~/.icons as well: a running Hyprland doesn't always notice themes newly
# added to ~/.local/share/icons, but finds them in ~/.icons.
CURSOR_THEME=dungeonOS-cursor
CURSOR_SIZE=64
for theme in miku-cursor-linux dungeonOS-cursor; do
    link "$DOTFILES/cursor/$theme" "$DATA/icons/$theme"
    link "$DOTFILES/cursor/$theme" "$HOME/.icons/$theme"
done

# The "default" theme is what anything falls back to when it isn't told a theme by
# name; point it at ours so nothing drops back to plain Miku. (nwg-look rewrites
# this file if you change the cursor there.)
mkdir -p "$DATA/icons/default"
printf '[Icon Theme]\nName=Default\nComment=Default Cursor Theme\nInherits=%s\n' "$CURSOR_THEME" > "$DATA/icons/default/index.theme"
echo "  default cursor theme -> $CURSOR_THEME"

if command -v gsettings >/dev/null; then
    gsettings set org.gnome.desktop.interface cursor-theme "$CURSOR_THEME"
    gsettings set org.gnome.desktop.interface cursor-size "$CURSOR_SIZE"
    echo "  gsettings cursor set"
fi
for gtk in gtk-3.0 gtk-4.0; do
    ini="$CONFIG/$gtk/settings.ini"
    mkdir -p "$(dirname "$ini")"
    [ -f "$ini" ] || printf '[Settings]\n' > "$ini"
    for kv in "gtk-cursor-theme-name=$CURSOR_THEME" "gtk-cursor-theme-size=$CURSOR_SIZE"; do
        key="${kv%%=*}"
        if grep -q "^$key=" "$ini"; then
            sed -i "s|^$key=.*|$kv|" "$ini"
        else
            sed -i "/^\[Settings\]/a $kv" "$ini"
        fi
    done
    echo "  $gtk cursor set"
done

# Apply now if we're inside a running Hyprland session
if [ -n "${HYPRLAND_INSTANCE_SIGNATURE:-}" ]; then
    hyprctl setcursor "$CURSOR_THEME" "$CURSOR_SIZE" >/dev/null && echo "  applied to running Hyprland"
fi

# ---------------------------------------------------------------------------
section "GTK theme"
# ---------------------------------------------------------------------------
# dungeonOS = GTK's own dark themes recoloured (gtk/make-theme.py); themes Nemo, file
# dialogs, pavucontrol and other GTK3/GTK4 apps
link "$DOTFILES/gtk/dungeonOS" "$DATA/themes/dungeonOS"
for gtk in gtk-3.0 gtk-4.0; do      # GTK3 apps (Nemo, ...) and GTK4 apps (pavucontrol, ...)
    ini="$CONFIG/$gtk/settings.ini"
    mkdir -p "$(dirname "$ini")"
    [ -f "$ini" ] || printf '[Settings]\n' > "$ini"
    if grep -q '^gtk-theme-name=' "$ini"; then
        sed -i 's|^gtk-theme-name=.*|gtk-theme-name=dungeonOS|' "$ini"
    else
        sed -i '/^\[Settings\]/a gtk-theme-name=dungeonOS' "$ini"
    fi
done
command -v gsettings >/dev/null && gsettings set org.gnome.desktop.interface gtk-theme dungeonOS
echo "  gtk theme -> dungeonOS"

# ---------------------------------------------------------------------------
section "Scripts"
# ---------------------------------------------------------------------------
# waybar, hyprland and the plugin builder call these by their ~/Dotfiles path
chmod +x "$DOTFILES"/scripts/*.sh "$DOTFILES"/hypr/plugins/build.sh
echo "  marked executable"
if [ "$DOTFILES" != "$HOME/Dotfiles" ]; then
    echo "  WARNING: configs expect this repo at ~/Dotfiles (it is at $DOTFILES)"
fi

# ---------------------------------------------------------------------------
section "Hyprland plugins"
# ---------------------------------------------------------------------------
# borders-plus-plus is compiled for the installed Hyprland; rerun build.sh after Hyprland updates
if command -v Hyprland >/dev/null; then
    "$DOTFILES/hypr/plugins/build.sh" || echo "  plugin build failed; Hyprland will fall back to the plain border"
else
    echo "  Hyprland not installed; skipped"
fi

# ---------------------------------------------------------------------------
section "Login screen"
# ---------------------------------------------------------------------------
# SDDM theme + its fonts, wallpaper and cursor go into system folders (asks for sudo)
if command -v sddm >/dev/null; then
    "$DOTFILES/sddm/install.sh" || echo "  login screen install failed; run sddm/install.sh later"
else
    echo "  SDDM not installed; skipped"
fi

# ---------------------------------------------------------------------------
section "Signal theme"
# ---------------------------------------------------------------------------
if command -v signal-desktop >/dev/null; then
    "$DOTFILES/signal/install.sh" || echo "  Signal theme failed; run signal/install.sh later"
else
    echo "  Signal not installed; skipped"
fi

# ---------------------------------------------------------------------------
section "Shell"
# ---------------------------------------------------------------------------
FISH="$(command -v fish || true)"
if [ -z "$FISH" ]; then
    echo "  fish not installed; skipped"
elif [ "$(realpath "$(getent passwd "$USER" | cut -d: -f7)")" = "$(realpath "$FISH")" ]; then
    echo "  ok    login shell is already fish"
else
    chsh -s "$FISH" && echo "  login shell set to fish (takes effect on next login)"
fi

section "Finished!"
# A kernel update removes the running kernel's modules folder, so drivers can't load
# until a reboot; otherwise logging out and back in is enough.
if [ ! -d "/usr/lib/modules/$(uname -r)" ]; then
    echo "The kernel was updated: reboot, then pick the Hyprland (uwsm) session at login."
else
    echo "Log out and pick the Hyprland (uwsm) session at login (no reboot needed)."
fi
