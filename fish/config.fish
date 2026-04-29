if status is-interactive
    # Commands to run in interactive sessions can go here

    echo -e "\033[0;31m♰ Ƿ𝖊𝖘 𝖍𝖆̄𝖑 ♰"
   





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


# Created by `pipx` on 2024-07-16 11:13:12
set PATH $PATH /home/maka/.local/bin
