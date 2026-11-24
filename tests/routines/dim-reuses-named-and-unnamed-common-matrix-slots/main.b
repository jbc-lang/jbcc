N = 2
COMMON A(2)
COMMON /CACHE/ Rows(N,3), Tail
A(2) = 'unnamed'
Rows(2,3) = 'named'
Tail = 'tail'
DIM A(2), Rows(2,3)
DIMENSION Rows(N,3)
IF 0 THEN DIM Rows(4,3)
CALL UPDATE()
CRT A(2):':':Rows(2,3):':':Tail
