EQU ADD TO 200
EQU STEP TO 700
N = 1
* full-line comment
again: CALL *ADD(N);* trailing comment
IF N = 2 THEN CALL 'ADD-STEP'(N)
CALL \*ADD\(N)
CALL '"SUMMARY"'(N)
Name = '*ADD'
CALL @Name(N)
CRT N
