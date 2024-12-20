#!/bin/bash

# bash dotfiles
echo "Creating symbolic links for bash dotfiles..."
ln -sf ~/Dotfiles/bash/.bashrc ~/
ln -sf ~/Dotfiles/bash/.bash_profile ~/

# cursor files
echo "Creating symbolic links for cursor, will prompt for password..."
sudo ln -sf ~/Dotfiles/cursor/miku-cursor-linux /usr/share/icons

hyprctl setcursor /usr/share/icons/miku-cursor-linux 57

# fonts
echo "Creating symbolic links for fonts..."
ln -sf ~/Dotfiles/fonts ~/.local/share

# font config
echo "Creating symbolic links for font config..."
ln -sf ~/Dotfiles/fontconfig ~/.config

# fuzzel
echo "Creating symbolic links for fuzzel..."
ln -sf ~/Dotfiles/fuzzel ~/.config

# hyprland & hyprpaper
echo "Creating symbolic links for hyprland and hyprpaper..."
ln -sf ~/Dotfiles/hypr ~/.config

# kitty
echo "Creating symbolic links for kitty..."
ln -sf ~/Dotfiles/kitty ~/.config

# alacritty
echo "Creating symbolic links for alacritty..."
ln -sf ~/Dotfiles/alacritty ~/.config

# nvim
echo "Creating symbolic links for nvim..."
ln -sf ~/Dotfiles/nvim ~/.config

# waybar
echo "Creating symbolic links for waybar..."
ln -sf ~/Dotfiles/waybar ~/.config

# BetterDiscord
echo "Creating symbolic links for better discord..."
ln -sf ~/Dotfiles/BetterDiscord ~/.config

# cmus
echo "Creating symbolic links for cmus..."
ln -sf ~/Dotfiles/cmus ~/.config

# btop
echo "Creating symbolic links for btop..."
ln -sf ~/Dotfiles/btop ~/.config

# neofetch
echo "Creating symbolic links for neofetch..."
ln -sf ~/Dotfiles/neofetch ~/.config

# yazi
echo "Creating symbolic links for yazi..."
ln -sf ~/Dotfiles/yazi ~/.config

# cava
echo "Creating symbolic links for cava..."
ln -sf ~/Dotfiles/cava ~/.config

# fish
echo "Creating symbolic links for fish..."
ln -sf ~/Dotfiles/fish ~/.config

echo "Finished!"
