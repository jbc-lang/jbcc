* tafc-emulation: prime
* TAFC-CROSSCHECK.md: MATBUILD without an end leaves out trailing empty
* elements; T24 builds records from R.NEW this way.
DIM M(6)
MAT M = ''
M(1) = 'a'
M(3) = 'c'
MATBUILD X FROM M
CRT '<' : OCONV(X, 'MCP') : '>'
M(6) = 'f'
MATBUILD X FROM M
CRT '<' : OCONV(X, 'MCP') : '>'
MAT M = ''
MATBUILD X FROM M
CRT '<' : OCONV(X, 'MCP') : '>'
MAT M = ''
M(2) = 'b'
MATBUILD X FROM M USING @VM
