local modes = {'n', 'v', 'o' }
local keys = {
  b = 'n',  -- Find "next" 
  j = 'e',  -- End of Word
  k = 'i',  -- Insert
  w = 'o',  -- Open Below

  n = 'b',  -- Go Previous Word
  e = 'j',  -- Go Up
  i = 'k',  -- Go Down
  o = 'w',  -- Go Next Word

  h = 's',  -- substitute char
  l = 't',  -- until char
  
  s = 'h',  -- Go Left  
  t = 'l',  -- Go Right

  d = 'r',  -- Replace
  r = 'd'   -- Delete
}

-- Remap Keys
for _, mode in ipairs(modes) do
  for key, remap in pairs(keys) do
    vim.api.nvim_set_keymap(mode, key, remap, {noremap = true, silent = true})
    vim.api.nvim_set_keymap(mode, key:upper(), remap:upper(), {noremap = true, silent = true})
  end
end

vim.o.clipboard = "unnamedplus"