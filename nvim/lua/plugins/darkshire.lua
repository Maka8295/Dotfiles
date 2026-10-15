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
      }

      vim.cmd.colorscheme "everforest"

      local function dungeonOS()
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
          steel_dark = "#6B6862",

          rust = "#7B4A3E",
          border = "#7E705D",
        }

        local set = vim.api.nvim_set_hl

        -- editor
        set(0, "Normal", { fg = colors.fg, bg = colors.bg })
        set(0, "NormalFloat", { fg = colors.fg, bg = colors.surface })
        set(0, "CursorLine", { bg = colors.surface })
        set(0, "Visual", { bg = colors.selection })

        -- syntax
        set(0, "Comment", { fg = colors.comment, italic = false })
        set(0, "Function", { fg = colors.moss })
        set(0, "String", { fg = colors.sage })
        set(0, "Keyword", { fg = colors.brass })
        set(0, "Type", { fg = colors.steel })
        set(0, "Constant", { fg = colors.clay })

        -- diagnostics
        set(0, "DiagnosticError", { fg = colors.rust })
        set(0, "DiagnosticWarn", { fg = colors.brass })
        set(0, "DiagnosticInfo", { fg = colors.steel })
        set(0, "DiagnosticHint", { fg = colors.sage })

        -- UI
        set(0, "LineNr", { fg = colors.comment })
        set(0, "CursorLineNr", { fg = colors.brass, bold = true })

        -- telescope
        set(0, "TelescopeNormal", { bg = colors.bg_dark })
        set(0, "TelescopeBorder", { fg = colors.border, bg = colors.bg_dark })
        set(0, "TelescopeSelection", { bg = colors.selection })

        -- popup menu
        set(0, "Pmenu", { fg = colors.fg, bg = colors.surface })
        set(0, "PmenuSel", { fg = colors.bg, bg = colors.moss })

        -- statusline
        set(0, "StatusLine", { fg = colors.fg, bg = colors.surface })
      end

      dungeonOS()

      vim.api.nvim_create_autocmd("ColorScheme", {
        pattern = "*",
        callback = function()
          vim.schedule(function() dungeonOS() end)
        end,
      })
    end,
  },
}
