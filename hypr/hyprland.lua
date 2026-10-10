-- Hyprland Lua config (converted from hyprland.conf, targets Hyprland 0.55+)
-- Docs: https://wiki.hypr.land/configuring/

------------------
---- MONITORS ----
------------------

hl.monitor({
    output   = "DP-3",
    mode     = "2560x1440@200",
    position = "0x0",
    scale    = 1,
})

---------------------
---- MY PROGRAMS ----
---------------------

local terminal    = "kitty fish"
local browser     = "firefox"
local fileManager = "kitty yazi"
local menu        = "fuzzel --show drun"
local calc        = "/usr/bin/flatpak run --branch=stable --arch=x86_64 --command=qalculate-qt io.github.Qalculate.qalculate-qt"
local music       = "kitty --override font_size=14 -e cmus"
local cava        = "kitty --override font_size=1 -e cava"

-------------------
---- AUTOSTART ----
-------------------

hl.on("hyprland.start", function()
    hl.exec_cmd("hyprpaper")
    hl.exec_cmd("hyprctl setcursor miku-cursor-linux 57")
    hl.exec_cmd("waybar")

    -- FIX: the old config launched "kitty fish --class cmus-term -e cmus".
    -- Everything after "fish" is passed to fish, not kitty, so the class was
    -- never set and the cmus-scratchpad rule below could never match.
    hl.exec_cmd("kitty --class cmus-term -e cmus")
    hl.exec_cmd("signal-desktop")
end)

-- Send these to the special:magic workspace (Super+B) without switching to it
hl.window_rule({
    name  = "signal-scratchpad",
    match = { class = "^([Ss]ignal)$" },
    workspace = "special:magic silent",
})

hl.window_rule({
    name  = "cmus-scratchpad",
    match = { class = "^(cmus-term)$" },
    workspace = "special:magic silent",
})

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

hl.env("XCURSOR_SIZE", "57")
hl.env("HYPRCURSOR_SIZE", "57")

-----------------------
---- LOOK AND FEEL ----
-----------------------

hl.config({
    general = {
        gaps_in     = 10,
        gaps_out    = 18,
        border_size = 0,

        col = {
            active_border   = "rgb(8aadf4)",
            inactive_border = "rgb(5b6078)",
        },

        resize_on_border = false,
        allow_tearing    = false,
        layout           = "dwindle",
    },

    decoration = {
        rounding         = 0,
        active_opacity   = 1.0,
        inactive_opacity = 1.0,

        shadow = {
            enabled      = true,
            range        = 15,
            render_power = 3,
            color        = 0xee1a1a1a,
        },

        blur = {
            enabled  = false, -- false removes white pixels on curved edges
            size     = 3,
            passes   = 1,
            vibrancy = 0.1696,
        },
    },

    animations = {
        enabled = true,
    },

    dwindle = {
        preserve_split = true,
    },

    misc = {
        force_default_wallpaper = -1,
        disable_hyprland_logo   = true,
    },
})

hl.curve("myBezier", { type = "bezier", points = { {0.05, 0.9}, {0.1, 1.05} } })

hl.animation({ leaf = "windows",    enabled = true, speed = 7,  bezier = "myBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 7,  bezier = "default", style = "popin 80%" })
hl.animation({ leaf = "border",     enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "borderangle",enabled = true, speed = 8,  bezier = "default" })
hl.animation({ leaf = "fade",       enabled = true, speed = 7,  bezier = "default" })
hl.animation({ leaf = "workspaces", enabled = true, speed = 6,  bezier = "default" })

---------------------
---- KEYBINDINGS ----
---------------------

local mainMod = "SUPER"

-- Brightness
hl.bind("XF86MonBrightnessUp",   hl.dsp.exec_cmd("brightnessctl s +5%"))
hl.bind("XF86MonBrightnessDown", hl.dsp.exec_cmd("brightnessctl s 5%-"))

-- Audio (repeat while held / work while locked, like the old bindel/bindl)
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind("XF86AudioLowerVolume", hl.dsp.exec_cmd("wpctl set-volume @DEFAULT_AUDIO_SINK@ 5%-"), { locked = true, repeating = true })
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true })

-- Macro for bluetooth <-> DAC
hl.bind(mainMod .. " + Escape", hl.dsp.exec_cmd("~/Dotfiles/scripts/toggle-audio.sh"))

-- Apps / window management
hl.bind(mainMod .. " + F", hl.dsp.exec_cmd(terminal))
hl.bind(mainMod .. " + R", hl.dsp.window.close())
hl.bind(mainMod .. " + D", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + T", hl.dsp.exec_cmd(browser))
hl.bind(mainMod .. " + G", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + S", hl.dsp.exec_cmd(menu))

-- Fullscreen (old: "fullscreen, 0")
hl.bind(mainMod .. " + A", hl.dsp.window.fullscreen({ mode = "fullscreen", action = "toggle" }))

-- Move focus
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
hl.bind(mainMod .. " + right", hl.dsp.focus({ direction = "right" }))
hl.bind(mainMod .. " + up",    hl.dsp.focus({ direction = "up" }))
hl.bind(mainMod .. " + down",  hl.dsp.focus({ direction = "down" }))

-- Workspaces 1-10 (key 0 = workspace 10)
for i = 1, 10 do
    local key = i % 10
    hl.bind(mainMod .. " + " .. key,           hl.dsp.focus({ workspace = i }))
    hl.bind(mainMod .. " + SHIFT + " .. key,   hl.dsp.window.move({ workspace = i }))
end

-- Special workspace (scratchpad)
hl.bind(mainMod .. " + B",         hl.dsp.workspace.toggle_special("magic"))
hl.bind(mainMod .. " + SHIFT + B", hl.dsp.window.move({ workspace = "special:magic" }))

-- Scroll through workspaces
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse_up",   hl.dsp.focus({ workspace = "e-1" }))

-- Move / resize with mouse
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind(mainMod .. " + mouse:273", hl.dsp.window.resize(), { mouse = true })

--------------------------------
---- WINDOWS AND WORKSPACES ----
--------------------------------

-- FIX for new terminals opening full screen:
-- Apps (kitty included) can ask to be maximized when they open. Without this
-- rule Hyprland honours that request and the window ignores tiling until you
-- toggle fullscreen on and off. This is in Hyprland's default config.
hl.window_rule({
    name  = "suppress-maximize-events",
    match = { class = ".*" },

    suppress_event = "maximize",
})

hl.workspace_rule({ workspace = "1", monitor = "DP-1", persistent = true })
hl.workspace_rule({ workspace = "2", monitor = "DP-1", persistent = true })
hl.workspace_rule({ workspace = "3", monitor = "DP-3", persistent = true })
hl.workspace_rule({ workspace = "4", monitor = "DP-3", persistent = true })
