S = 'a--b----c--'
PRINT COUNT('jjjjj','jjj'), DCOUNT(S,'--'), LEN(FIELD(S,'--',2,2))
PRINT FIELD(S,'--',2,2), FIELD(S,'--',4,9)
PRINT COUNT('',@FM), DCOUNT('',@FM), DCOUNT('A':@FM:'B',@FM)
PRINT NOT('0.00'), NOT('yes')
EQU FM TO @FM
PRINT DCOUNT('A' : FM : 'B', @FM)
S = 'QWE'
S:='RT'
S := 120 + 3
PRINT S
DIM M(2)
MAT M = 'item'
M(2) := 2
PRINT M(1), M(2)
R = 'abc' : @AM : 'xy'
R<2>:='z'
R<1>[2,1] := '!'
PRINT R<1>, R<2>
S = 'start'
FOR I = 1 TO 2
  S := ':' : I
NEXT
PRINT S
