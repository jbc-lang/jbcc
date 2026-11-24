COM /EXAMPLE/ X, A(2),
   X, Y
COMMON Z, Z
COM /EXAMPLE/ X
X = 'caller'
A(2) = 'matrix'
FOR I = 1 TO 2
  CALL CHANGE(I)
NEXT
PRINT X, A(2), Y, Z
