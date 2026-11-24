N = 2
COMMON /SHARED/ Rows, Middle
COMMON /SHARED/ Rows(N), Tail
Rows(2) = 'row'
Middle = 'middle'
Tail = 'tail'
CALL UPDATE()
CRT Rows(2), Middle, Tail
