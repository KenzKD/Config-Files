local modes = {'n', 'v'}
local keys = {
  h = 'n',
  j = 'e',
  k = 'i',
  l = 'o',
  n = 'h',
  e = 'j',
  i = 'k',
  o = 'l'
}

for _, mode in ipairs(modes) do
  for key, remap in pairs(keys) do
    vim.api.nvim_set_keymap(mode, key, remap, {noremap = true, silent = true})
  end
end