EQU SIZE TO 2
DIM A(SIZE), B(2,3)
FOR I = 0 TO SIZE
  A(I) = I + 10
NEXT
B(1, 3) = A(0)
B(1, 3) += A(2)
CRT B(1, 3)
