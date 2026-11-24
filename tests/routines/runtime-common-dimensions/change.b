SUBROUTINE CHANGE()
N = 1
COMMON /CACHE/ H, M(2,N), T, X(3)
DIM Copy(2,1)
MAT Copy = MAT M
MAT Copy = Copy(2,1) : '!'
MAT M = MAT Copy
T := '!'
X(3) := '!'
