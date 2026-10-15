-- Hyprland Lua config (converted from hyprland.conf, targets Hyprland 0.55+)
-- Docs: https://wiki.hypr.land/configuring/

------------------
---- MONITORS ----
------------------

-- Desktop monitor
hl.monitor({
    output   = "DP-3",
    mode     = "2560x1440@200",
    position = "0x0",
    scale    = 1,
})

-- Laptop (ThinkPad T14 Gen 2, 14in 4K): scale 2 = exactly 2x2 screen pixels per UI pixel,
-- so the pixel art stays crisp (a fractional scale like 1.5 would blur it). Same layout
-- as a 1920x1080 screen.
hl.monitor({
    output   = "eDP-1",
    mode     = "3840x2160@60",
    position = "auto",
    scale    = 2,
})

-- Anything else (a TV, a projector, ...): its best resolution, placed and
-- scaled automatically, so this config works on any machine out of the box
hl.monitor({
    output   = "",
    mode     = "preferred",
    position = "auto",
    scale    = "auto",
})

---------------------
---- MY PROGRAMS ----
---------------------

local terminal    = "kitty fish"
local browser     = "firefox"
local fileManager = "kitty yazi"
local menu        = "rofi -show drun"
local calc        = "/usr/bin/flatpak run --branch=stable --arch=x86_64 --command=qalculate-qt io.github.Qalculate.qalculate-qt"
local music       = "kitty --override font_size=14 -e cmus"
local cava        = "kitty --override font_size=1 -e cava"

-------------------
---- AUTOSTART ----
-------------------

-- Scratchpad apps (Super+B): Signal on the right, cmus top-left, btop below it.
-- special:magic uses the master layout (see WINDOWS AND WORKSPACES), so the order apps
-- open in decides where they go; scripts/scratchpad.sh opens them one at a time. It runs
-- as its own process because a config reload at login (the border plugin loading) wiped
-- the waiting when it was done here in Lua, and cmus/btop never opened.

hl.on("hyprland.start", function()
    hl.exec_cmd("hyprpaper")
    -- 64 = the cursor art scaled exactly 2x, so its pixels stay sharp (57 blurred them)
    hl.exec_cmd("hyprctl setcursor dungeonOS-cursor 64")
    hl.exec_cmd("~/Dotfiles/scripts/waybar.sh")  -- remembers horizontal/vertical (scripts/waybar-toggle.sh)

    hl.exec_cmd("~/Dotfiles/scripts/scratchpad.sh")
    hl.exec_cmd("hypridle")   -- locks before sleep, idle lock/screen-off (hypr/hypridle.conf)
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

hl.window_rule({
    name  = "btop-scratchpad",
    match = { class = "^(btop-term)$" },
    workspace = "special:magic silent",
})

-------------------------------
---- ENVIRONMENT VARIABLES ----
-------------------------------

-- Cursor theme. XCURSOR_PATH is spelled out with full paths because Hyprland didn't
-- find cursor themes in ~/.icons or ~/.local/share/icons without it, and fell back to Miku.
hl.env("XCURSOR_PATH", os.getenv("HOME") .. "/.local/share/icons:" .. os.getenv("HOME") .. "/.icons:/usr/share/icons:/usr/share/pixmaps")
hl.env("XCURSOR_THEME", "dungeonOS-cursor")
hl.env("XCURSOR_SIZE", "64")
hl.env("HYPRCURSOR_THEME", "dungeonOS-cursor")
hl.env("HYPRCURSOR_SIZE", "64")

-----------------------
---- LOOK AND FEEL ----
-----------------------

hl.config({
    general = {
        -- every gap is 10px: screen edge <-> window, window <-> window (2 x gaps_in),
        -- waybar <-> window, and waybar's own margins in waybar/config.jsonc
        gaps_in     = 5,
        gaps_out    = 10,
        -- dungeonOS frame (matches waybar): 3px #463D34 border + 1px bronze outer rule (the sharp shadow below)
        border_size = 3,

        col = {
            active_border   = "rgb(463D34)",
            inactive_border = "rgb(463D34)",
        },

        resize_on_border = false,
        allow_tearing    = false,
        layout           = "dwindle",
    },

    decoration = {
        rounding         = 0,
        active_opacity   = 1.0,
        inactive_opacity = 1.0,

        -- sharp 1px "shadow" draws the outer rule of the frame; dims on unfocused windows
        -- (only used when borders-plus-plus isn't built — see below)
        shadow = {
            enabled        = true,
            sharp          = true,
            range          = 1,
            render_power   = 1,
            color          = 0xff7e705d,
            color_inactive = 0xff463d34,
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

    -- only used by the scratchpad (special:magic): new windows join the stack
    -- instead of replacing the master, and master/stack split the screen in half
    master = {
        new_status = "slave",
        mfact      = 0.5,
    },

    misc = {
        force_default_wallpaper = -1,
        disable_hyprland_logo   = true,
    },
})

-- dungeonOS frame (same as waybar) via borders-plus-plus, drawn outward from the window:
--   3px #463D34 (Hyprland's border) | 1px #7E705D (plugin), with a soft shadow beneath
-- Build it with ~/Dotfiles/hypr/plugins/build.sh (rerun after Hyprland updates).
-- If it isn't built, the sharp-shadow frame configured above is used instead.
local bordersPlusPlus = os.getenv("HOME") .. "/.local/share/hypr/plugins/borders-plus-plus.so"
local bppFile = io.open(bordersPlusPlus, "r")
if bppFile then
    bppFile:close()
    hl.plugin.load(bordersPlusPlus)

    hl.config({
        general = {
            border_size = 3,
            col = {
                active_border   = "rgb(463D34)",
                inactive_border = "rgb(463D34)",
            },
        },

        -- back to a soft drop shadow beneath the frame
        decoration = {
            shadow = {
                sharp          = false,
                range          = 15,
                render_power   = 3,
                color          = 0xee1a1a1a,
                color_inactive = 0xee1a1a1a,
            },
        },

        plugin = {
            borders_plus_plus = {
                add_borders      = 1,
                natural_rounding = true,
                col = {
                    border_1 = "rgb(7E705D)",
                },
                border_size_1 = 1,
            },
        },
    })
end

hl.curve("myBezier",{ type = "bezier", points = { {0.05, 0.9}, {0.1, 1.05} } })

hl.animation({ leaf = "windows",    enabled = true, speed = 7,  bezier = "myBezier" })
hl.animation({ leaf = "windowsOut", enabled = true, speed = 7,  bezier = "default", style = "popin 80%" })
hl.animation({ leaf = "border",     enabled = true, speed = 10, bezier = "default" })
hl.animation({ leaf = "borderangle",enabled = true, speed = 8,  bezier = "default" })
hl.animation({ leaf = "fade",       enabled = true, speed = 7,  bezier = "default" })
-- Workspaces slide the same way as the waybar layout (scripts/waybar-toggle.sh switches it):
-- up/down with the vertical bar (default), left/right with the horizontal one
local barLayoutFile = io.open((os.getenv("XDG_STATE_HOME") or (os.getenv("HOME") .. "/.local/state")) .. "/waybar-layout")
local barLayout = barLayoutFile and barLayoutFile:read("l") or "vertical"
if barLayoutFile then barLayoutFile:close() end
hl.animation({ leaf = "workspaces", enabled = true, speed = 6,  bezier = "default",
               style = barLayout == "horizontal" and "slide" or "slidevert" })

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
hl.bind(mainMod .. " + E", hl.dsp.exec_cmd("nemo"))   -- graphical file manager ("Files")
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

-- Lock the screen (hyprlock, via hypridle so there is only ever one lock screen)
hl.bind(mainMod .. " + L", hl.dsp.exec_cmd("loginctl lock-session"))

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

-- Not pinned to a monitor name, so they work on whatever screen the machine has
hl.workspace_rule({ workspace = "1", persistent = true, default = true })
hl.workspace_rule({ workspace = "2", persistent = true })
hl.workspace_rule({ workspace = "3", persistent = true })
hl.workspace_rule({ workspace = "4", persistent = true })

-- Scratchpad layout: master (Signal) on the right, stack (cmus, btop) on the left
hl.workspace_rule({ workspace = "special:magic", layout = "master", layout_opts = { orientation = "right" } })
