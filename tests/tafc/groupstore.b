* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: GROUPSTORE, from the guide's example.
to.var = 'QQQ' :@FM: 'WWW' :@FM: 'EEE'
from.var = 'rtz'
GROUPSTORE from.var IN to.var USING 2, 0, @FM
CRT FMT(to.var, 'MCP')
GROUPSTORE from.var IN to.var USING 4, 1
CRT FMT(to.var, 'MCP')
GROUPSTORE from.var IN to.var USING 2, 0, @VM
CRT FMT(to.var, 'MCP')
X = 'a-b-c' ; GROUPSTORE 'Z':@FM:'Y' IN X USING 2, 2, '-' ; CRT FMT(X, 'MCP')
X = 'a-b-c' ; GROUPSTORE 'Z' IN X USING 5, 1, '-' ; CRT FMT(X, 'MCP')
X = 'a-b-c' ; GROUPSTORE 'Z' IN X USING 0, 1, '-' ; CRT FMT(X, 'MCP')
X = '' ; GROUPSTORE 'Z' IN X USING 1, 1 ; CRT FMT(X, 'MCP')
