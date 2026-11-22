EQU SIZE TO 2
DIM A(SIZE), B(2,3)
FOR I = 0 TO SIZE
  A(I) = I + 10
NEXT
B(1, 3) = A(0)
B(1, 3) += A(2)
CRT B(1, 3)
COMMON /WORK/ Prefix, Shared(2,3), Suffix
Prefix = 'before'
Suffix = 'after'
FOR I = 1 TO 2
  MAT B = 'pass' : I
  B(2,3) = B(0,0) : '!'
  MAT Shared = MAT B
NEXT
MAT Shared = MAT Shared
MAT B = Shared(2,3)
Shared(2,3) = 'changed'
CRT B(0,0), B(2,3), Shared(0,0), Shared(2,3)
CRT Prefix, Suffix
MAT Shared = ''
MAT B = MAT Shared
CRT '[' : B(1,2) : ']'
