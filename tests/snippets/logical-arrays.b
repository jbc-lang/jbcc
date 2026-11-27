* Guide ANDS, ORS and MODS examples.
A = 1 :@SM: 4 :@VM: 4 :@SM: 1
B = 1 :@SM: 1 - 1 :@VM: 2
CRT OCONV( ANDS(A, B), 'MCP' )
A = "A" :@SM: 0 :@VM: 4 :@SM: 1
B = 0 :@SM: 1-1 :@VM: 2
CRT OCONV( ORS(A, B), 'MCP')
A = 3 :@VM: 7
B = 2: @SM: 7 :@VM: 4
CRT OCONV( MODS(A, B), 'MCP' )
* Null elements: ANDS and ORS give null for a pair of nulls, ORS gives
* true beside a true value, and MODS gives null and 0 for a zero divisor.
CRT OCONV( ANDS('' :@VM: '' :@VM: 0, '' :@VM: 0 :@VM: ''), 'MCP' )
CRT OCONV( ORS('' :@VM: '' :@VM: '', '' :@VM: 0 :@VM: 5), 'MCP' )
CRT OCONV( MODS('' :@VM: 5 :@VM: -7, 3 :@VM: 0 :@VM: 3), 'MCP' )
* Guide IFS example; TAFC prints This^is]how\Globus^works.
C = 1 :@FM: 0 :@VM: 1 :@SM: 0 :@FM: 1
T = 'This' :@FM: 'was' :@VM: 'how' :@SM: 'system' :@FM: 'works'
F = 'That' :@FM: 'is' :@VM: 'how' :@SM: 'Globus' :@FM: 'worked'
CRT CONVERT(@FM:@VM:@SM, '^]\', IFS(C, T, F))
CRT CONVERT(@VM, ']', IFS(1 :@VM: '' :@VM: 1, 'a', 'b' :@VM: 'c'))
