CRT EREPLACE('aaaaa', 'aa', 'b')
CRT EREPLACE('aaaaa', 'aa', 'b', 1)
CRT EREPLACE('aaaaa', 'aa', 'b', 0, 2)
CRT EREPLACE('aaaaa', 'aa', '', -1, 0)
CRT EREPLACE('tail', '', 'head:')
CRT CHANGE('tail', '', 'head:')
Value = 'cocoa'
EREPLACE 'co' WITH 'x' IN Value
CRT Value
