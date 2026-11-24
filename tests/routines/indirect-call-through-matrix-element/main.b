DEFFUN CHANGE.TARGET(Slot, Index)
DIM Names(2), Grid(1,1)
Names(1) = 'ADD'
Names(2) = 'REPORT'
Grid(1,0) = 'REPORT'
X = 2
I = 1
EQU Target TO Names(I)
CALL @Target(X, CHANGE.TARGET(Names(1), I))
CRT X
CRT I
CALL @Names(1)()
CALL @Names(2)
CALL @Grid(1, I - 2)
