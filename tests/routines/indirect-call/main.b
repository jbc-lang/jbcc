EQU Which TO Name
DEFFUN SWITCH(N)
DIM M(2)
M(1) = 4
X = 1
Name = '!WORK'
CALL @Which(MAT M, X, X, SWITCH(Name))
CRT M(1), X
CALL @ Name
