-- dungeonOS: everforest rebuilt from the dungeonOS palette.
--
-- The colours go in through everforest's own hooks (colours_override for the palette,
-- on_highlights for individual groups) rather than by overriding highlight groups after
-- the theme loads. Overriding afterwards only caught the classic groups (Function, String,
-- ...), but code in any language with a treesitter parser or an LSP is coloured through
-- @function, @string, @lsp.type.* ... which stayed everforest green/red/yellow, so the
-- theme looked like it only loaded "sometimes" (depending on the file type, and changing
-- a moment after opening when the LSP attached).
local colors = {
  bg = "#1A1816",
  bg_dark = "#141210",
  surface = "#24201C",
  selection = "#463D34",

  fg = "#C8B8A0",
  fg_muted = "#9D8E7C",
  comment = "#6F675E",

  moss = "#6E7F5A",
  sage = "#879376",

  brass = "#A88A5B",
  clay = "#7A5E47",

  steel = "#8F8B81",

  rust = "#7B4A3E",
  border = "#7E705D",
}

return {
  {
    "neanias/everforest-nvim",
    priority = 1000,
    config = function()
      require("everforest").setup {
        background = "hard",
        transparent_background_level = 0,
        italics = false,
        disable_italic_comments = true,

        -- everforest's palette slots -> dungeonOS. The accents keep their everforest
        -- meanings (red = errors, yellow = warnings, green = functions/added, aqua = strings)
        colours_override = function(p)
          p.bg_dim = colors.bg_dark
          p.bg0 = colors.bg
          p.bg1 = colors.surface
          p.bg2 = colors.surface
          p.bg3 = colors.selection
          p.bg4 = colors.selection
          p.bg5 = colors.border
          p.bg_visual = colors.selection
          p.bg_red = "#33221E"
          p.bg_green = "#272A20"
          p.bg_blue = "#272724"
          p.bg_yellow = "#2F281E"
          p.bg_purple = "#2C2420"

          p.fg = colors.fg
          p.grey0 = colors.comment
          p.grey1 = colors.comment
          p.grey2 = colors.fg_muted

          p.red = colors.rust
          p.orange = colors.clay
          p.yellow = colors.brass
          p.green = colors.moss
          p.aqua = colors.sage
          p.blue = colors.steel
          p.purple = colors.clay

          p.statusline1 = colors.moss
          p.statusline2 = colors.fg
          p.statusline3 = colors.rust
        end,

        on_highlights = function(hl)
          -- everforest colours keywords like errors (red) and types like warnings (yellow);
          -- dungeonOS has keywords in brass and types in steel, errors/warnings unchanged.
          -- Treesitter groups (TS*, which the @ groups and LSP tokens link to) follow suit.
          local relink = {
            Red = "Keyword", RedItalic = "Keyword", RedBold = "Keyword",
            Yellow = "Type", YellowItalic = "Type", YellowBold = "Type",
          }
          for name, spec in pairs(hl) do
            if name:find "TS" and relink[spec.link] then spec.link = relink[spec.link] end
          end

          -- editor
          hl.Normal = { fg = colors.fg, bg = colors.bg }
          hl.NormalFloat = { fg = colors.fg, bg = colors.surface }
          hl.CursorLine = { bg = colors.surface }
          hl.Visual = { bg = colors.selection }

          -- syntax
          hl.Comment = { fg = colors.comment }
          hl.Function = { fg = colors.moss }
          hl.String = { fg = colors.sage }
          hl.Keyword = { fg = colors.brass }
          hl.Type = { fg = colors.steel }
          hl.Constant = { fg = colors.clay }

          -- UI
          hl.LineNr = { fg = colors.comment }
          hl.CursorLineNr = { fg = colors.brass, bold = true }

          -- telescope
          hl.TelescopeNormal = { bg = colors.bg_dark }
          hl.TelescopeBorder = { fg = colors.border, bg = colors.bg_dark }
          hl.TelescopeSelection = { bg = colors.selection }

          -- popup menu
          hl.Pmenu = { fg = colors.fg, bg = colors.surface }
          hl.PmenuSel = { fg = colors.bg, bg = colors.moss }

          -- statusline
          hl.StatusLine = { fg = colors.fg, bg = colors.surface }
        end,
      }

      vim.cmd.colorscheme "everforest"
    end,
  },
}
