PROMPT ''
FOR I = 1 TO 2
    DATA 'item-':I
NEXT I
DATA 'abc':@FM:'', 'next'
INPUT A
INPUT B
INPUT Prefix, 2
INPUT Suffix
INPUT EmptyLine
INPUT Last
CRT A:':':B:':':Prefix:':':Suffix:'[':EmptyLine:']:':Last
DATA 'child-1':@FM:'child-2', ''
EXECUTE 'cat' CAPTURING Captured RETURNING Result
CRT CONVERT(Captured, @FM, '|'):':':Result
DATA 'direct'
PERFORM 'cat'
DATA STR('x', 100000)
EXECUTE 'true'
INPUT FromStdin
CRT FromStdin
