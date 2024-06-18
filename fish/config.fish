if status is-interactive
    # Commands to run in interactive sessions can go here
end

## nvim transparency
function nvim
    # Set background opacity to 1 (opaque)
    kitty @ set-background-opacity 1

    # Launch Neovim
    command nvim $argv

    # Restore the original background opacity when Neovim exits
    kitty @ set-background-opacity 0.8
end

