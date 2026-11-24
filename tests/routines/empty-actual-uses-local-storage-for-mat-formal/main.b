DIM Values(2)
Name = 'LOAD.VALUES'
CALL LOAD.VALUES('', 3, Result)
CRT Result
CALL @Name("", 4, Result)
CRT Result
CALL LOAD.VALUES(MAT Values, 2, Result)
CRT Result, Values(2)
CALL CHECK.SCALAR('', Result)
CRT '[':Result:']'
