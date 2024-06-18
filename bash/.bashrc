#
# ~/.bashrc
#

# If not running interactively, don't do anything
[[ $- != *i* ]] && return

alias ls='ls --color=auto'
alias grep='grep --color=auto'
PS1='[\u@\h \W]\$ '

if [ -z "${WAYLAND_DISPLAY}" ] && [ "${XDG_VTNR}" -eq 1 ]; then
    dbus-run-session Hyprland
fi

# thing for wofi to find flatpak
export XDG_DATA_DIRS=/var/lib/flatpak/exports/share:/usr/local/share:/usr/share

# for Japanese input
export GTK_IM_MODULE='fcitx'
export QT_IM_MODULE='fcitx'
export SDL_IM_MODULE='fcitx'
export XMODIFIERS='@im=fcitx'

# setting default text editor
export EDITOR=nvim

# turrning off translucency for nvim

nvim() {

    # Set background opacity to 1 (opaque)
    kitty @ set-background-opacity 1

    # Launch Neovim
    command nvim "$@"

    # Restore the original background opacity when Neovim exits
    kitty @ set-background-opacity 0.8
}

