N = 2
COMMON /DATA/ Grid(N,3)
DIM Copy(N,3)
MAT Grid = 'seed'
CALL RELAY(MAT Grid, MAT Copy, N, Result)
PRINT Grid(0,0), Grid(2,3), Copy(2,3), Result
