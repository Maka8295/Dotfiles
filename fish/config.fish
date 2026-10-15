if status is-interactive
    # Commands to run in interactive sessions can go here

    # a random Old English phrase and its translation (fish/functions/dungeon_greeting.fish,
    # phrases in fish/greetings.txt)
    dungeon_greeting
   





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
