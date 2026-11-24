N = 2
Rows = 'scalar'
CALL APPEND(Rows)
CRT Rows
DIM Rows(N)
CRT ASSIGNED(Rows(0))
Rows(1) = 'matrix'
CALL APPEND(Rows(1))
CRT Rows(1)
