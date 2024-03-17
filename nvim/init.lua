local modes = {'n', 'v'}
local keys = {
  h = 'n',
  j = 'e',
  k = 'i',
  l = 'o',
  n = 'h',
  e = 'j',
  i = 'k',
  o = 'l',

  w = 't',
  b = 'r',
  r = 'b',
  t = 'w'
}

for _, mode in ipairs(modes) do
  for key, remap in pairs(keys) do
    vim.api.nvim_set_keymap(mode, key, remap, {noremap = true, silent = true})
    vim.api.nvim_set_keymap(mode, key:upper(), remap:upper(), {noremap = true, silent = true})
  end
end

vim.o.clipboard = "unnamedplus"