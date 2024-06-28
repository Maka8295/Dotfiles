if status is-interactive
    # Commands to run in interactive sessions can go here

    echo -e "\033[0;31m󰊠 \033[0m""\033[0;33m󰊠 \033[0m""\033[0;32m󰊠 \033[0m""\033[0;35m󰊠 \033[0m""\033[0;34m󰊠 \033[0m""\033[0;36m󰊠 \033[0m"
   





end

## nvim transparency
function nvim
    # Set background opacity to 1 (opaque)
    kitty @ set-background-opacity 1

    # Launch Neovim
    command nvim $argv

    # Restore the original background opacity when Neovim exits
    kitty @ set-background-opacity 1
end

