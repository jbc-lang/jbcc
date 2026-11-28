* tafc-emulation: prime
* TAFC-CROSSCHECK.md: a local DIM run again resizes the matrix and keeps
* the elements in their linear order.
DIM X(3)
X(1) = "a" ; X(2) = "b" ; X(3) = "c"
DIM X(5)
CRT "grow [" : X(1) : "][" : X(3) : "][" : X(5) : "]"
DIM X(2)
CRT "shrink [" : X(1) : "][" : X(2) : "]"
DIM X(4)
CRT "regrow [" : X(3) : "][" : X(4) : "]"
DIM Y(2,2)
Y(2,2) = "q"
DIM Y(3,3)
CRT "two [" : Y(2,2) : "][" : Y(3,3) : "]"
FOR I = 1 TO 2
   DIM X(I * 3)
   MAT X = I
   X(I * 3) = "last" : I
   CRT "pass " : I : " [" : X(I * 3) : "] [" : X(1) : "]"
NEXT I
GOSUB SUB
GOSUB SUB
STOP
SUB:
DIM Z(3) ; MAT Z = ""
Z(2) = "y"
CRT "Z [" : Z(2) : "]"
RETURN
