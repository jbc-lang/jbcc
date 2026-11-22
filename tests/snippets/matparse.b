DIM Fields(5)
Record = 'aa' : @FM : '' : @FM : 'bb' : @FM : 'cc' : @FM
MATPARSE Fields FROM Record SETTING Used
MATBUILD Copy FROM Fields
PRINT Used, Copy = Record, LEN(Fields(0))
MAT Fields = 'keep'
MATPARSE Fields, 2, 4 FROM 'one|two|three|four||six' USING '|extra' SETTING Used
MATBUILD Copy FROM Fields USING '/'
PRINT Copy, Used, Fields(0)
MATPARSE Fields, 3 FROM Fields(0), '|' SETTING Fields(2)
MATBUILD Copy FROM Fields USING '/'
PRINT Copy, LEN(Fields(0))
N = 2
COMMON /Scratch/ Grid(N,2)
MATPARSE Grid FROM 'a:b:c', ':' SETTING Used
PRINT Grid(1,1), Grid(1,2), Grid(2,1), LEN(Grid(2,2)), Used
FOR I = 1 TO 2
    MATPARSE Grid, 2, 2 FROM 'X/' : I : '/Y' USING '/' SETTING Used
NEXT I
PRINT Grid(1,2), Grid(0,0), Used
MATPARSE Fields FROM '' SETTING Used
PRINT Used, LEN(Fields(1)), LEN(Fields(5)), LEN(Fields(0))
MATPARSE Fields FROM 'a|b' USING '' SETTING Used
PRINT Fields(1), Used
MATPARSE Fields, 5, 2 FROM 'skip' SETTING Used
PRINT Fields(1), Used
