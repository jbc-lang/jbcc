DIM Items(8)
FOR I = 1 TO 8
    Items(I) = 'v' : I
NEXT I
MATBUILD Selected FROM Items, 3, 7 USING ':ignored'
PRINT Selected
Items(4) = ''
MATBUILD Record FROM Items
PRINT CONVERT(Record, @FM, '|')
Limit = 2
COMMON /GridData/ Grid(Limit, 3)
FOR R = 1 TO 2
    FOR C = 1 TO 3
        Grid(R,C) = R : C
    NEXT C
NEXT R
MATBUILD Grid(2,1) FROM Grid, Limit + 1 USING '/'
PRINT Grid(2,1)
MATBUILD Items(0) FROM Items, 6, 8 USING ''
PRINT Items(0)
MATBUILD Backwards FROM Items, 3, 2
PRINT LEN(Backwards)
MATBUILD Suffix FROM Items, 7, -1, '!'
PRINT Suffix
