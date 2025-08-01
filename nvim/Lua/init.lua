local modes = { 'n', 'v', 'o' }

local keys = 
{
	b = 'n', -- Find "next"
	j = 'e', -- End of Word
	k = 'i', -- Insert
	w = 'o', -- Open Below

	n = 'b', -- Go Previous Word
	e = 'j', -- Go Up
	i = 'k', -- Go Down
	o = 'w', -- Go Next Word

	h = 's', -- Substitute Char
	l = 't', -- Until Char

	s = 'h', -- Go Left
	t = 'l', -- Go Right

	d = 'r', -- Replace
	r = 'd', -- Delete
}

-- Remap Keys
for _, mode in ipairs(modes) do
  	for key, remap in pairs(keys) do
		vim.api.nvim_set_keymap(mode, key, remap, { noremap = true, silent = true })
		vim.api.nvim_set_keymap(mode, key:upper(), remap:upper(), { noremap = true, silent = true })
  	end
end

-- Extra Key Mappings
local mappings = 
{
	--  Mode	Key			Command
	{   'n',    '<Tab>',   	'>>' 			},	-- Indent
	{   'v',    '<Tab>',   	'>gv' 			},
	{   'n',    '<S-Tab>', 	'<<' 			},	-- Outdent
	{   'v',    '<S-Tab>', 	'<gv' 			},
	{   'n',    '<BS>',    	'X' 			},	-- Delete Char
	{   'v',    '<BS>',    	'X' 			},
	{   'n',    '<CR>',    	'o<Esc>' 		},	-- New Line
	{   'v',    '<CR>',    	'<Esc>o<Esc>v' 	},
	{   'i',    'ii',      	'<Esc>' 		},	-- 'ii' is now Esc
}
	
for _, map in ipairs(mappings) do
	vim.api.nvim_set_keymap(map[1], map[2], map[3], { noremap = true, silent = true, nowait = true })
end

--[[
VS Code Shortcuts:

1. Deactivated Neovim Keybindings:
	- Ctrl+A, Ctrl+C, Ctrl+S, Ctrl+X, Ctrl+V, and Ctrl+Z

2. Extra Key Mappings:
	- "ii" is now a shortcut for Esc
	- Tab, BackSpace and Enter Work as usual in Normal and Visual Mode
]]

-- Enable NeoVim Editor Features

-- Use OS Clipboard
vim.o.clipboard = "unnamedplus"

-- Show Line Numbers
vim.o.number = true
vim.o.relativenumber = true

-- Enable break indent
vim.o.breakindent = true

-- Save undo history
vim.o.undofile = true

-- Case-insensitive searching UNLESS \C or one or more capital letters in the search term
vim.o.ignorecase = true
vim.o.smartcase = true

-- Keep signcolumn on by default
vim.o.signcolumn = 'yes'

-- Decrease update time
vim.o.updatetime = 250

-- Decrease mapped sequence wait time
-- Displays which-key popup sooner
vim.o.timeoutlen = 300

-- Show which line your cursor is on
vim.o.cursorline = true

-- Minimal number of screen lines to keep above and below the cursor.
vim.o.scrolloff = 10

-- Enable mouse mode, can be useful for resizing splits for example!
vim.o.mouse = 'a'