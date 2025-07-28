" List of modes to iterate over
let s:modes = ['n', 'v', 'o']

" Mapping table: old_key → new_key
let s:keys = {
\   'b': 'n',
\   'j': 'e',
\   'k': 'i',
\   'w': 'o',
\   'n': 'b',
\   'e': 'j',
\   'i': 'k',
\   'o': 'w',
\   'h': 's',
\   'l': 't',
\   's': 'h',
\   't': 'l',
\   'd': 'r',
\   'r': 'd'
\}

for mode in s:modes
  for [key, remap] in items(s:keys)
    " lower-case mapping
    execute printf(
    \    '%snoremap <silent> %s %s',
    \    mode, key, remap
    \)
    " upper-case mapping
    execute printf(
    \    '%snoremap <silent> %s %s',
    \    mode, toupper(key), toupper(remap)
    \)
  endfor
endfor

" Extra key mappings
nnoremap <silent> <Tab>   >>
vnoremap <silent> <Tab>   >gv
nnoremap <silent> <S-Tab> <<
vnoremap <silent> <S-Tab> <gv
nnoremap <silent> <BS>    X
vnoremap <silent> <BS>    X
nnoremap <silent> <CR>    o<Esc>
vnoremap <silent> <CR>    <Esc>o<Esc>v
inoremap <silent> ii      <Esc>

" VS Code Shortcuts notes:
" 1. Deactivated Neovim keybindings: Ctrl+A, Ctrl+C, Ctrl+S, Ctrl+X, Ctrl+V, Ctrl+Z
" 2. ii → <Esc>, Tab/BackSpace/Enter as normal in N/V modes

" Enable Neovim Editor Features
set clipboard=unnamedplus       " Use OS clipboard
set number relativenumber       " Show absolute + relative line numbers
set breakindent                " Enable break indent
set undofile                   " Save undo history
set ignorecase smartcase       " Case-insensitive except with capitals
set signcolumn=yes             " Keep signcolumn visible
set updatetime=250             " Faster CursorHold
set timeoutlen=300             " Faster mapped sequence timeout
set cursorline                 " Highlight current line
set scrolloff=10               " Keep 10 lines above/below cursor
set mouse=a                    " Enable mouse support