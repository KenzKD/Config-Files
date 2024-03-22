local modes = {'n', 'v', 'o' }
local keys = {
  b = 'n',
  j = 'e',
  k = 'i',
  w = 'o',

  n = 'b',  -- Go Previous Word
  e = 'j',  -- Go Up
  i = 'k',  -- Go Down
  o = 'w',  -- Go Next Word

  h = 's', 
  l = 't',
  
  s = 'h',  -- Go Left  
  t = 'l',  -- Go Right

  d = 'r',
  r = 'd'   -- Delete
}

-- Remap Keys
for _, mode in ipairs(modes) do
  for key, remap in pairs(keys) do
    vim.api.nvim_set_keymap(mode, key, remap, {noremap = true, silent = true})
    vim.api.nvim_set_keymap(mode, key:upper(), remap:upper(), {noremap = true, silent = true})
  end
end

-- Remap "i" to "k" for Text Objects
local text_objects = {'w', 's', 'p', '"', '(', ')', '[', ']', '{', '}', 't'}
for _, object in ipairs(text_objects) do
  vim.api.nvim_set_keymap('o', 'k' .. object, 'i' .. object, {noremap = true, silent = true})
end

vim.o.clipboard = "unnamedplus"