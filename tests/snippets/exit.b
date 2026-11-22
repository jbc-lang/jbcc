J = 0
FOR I = 1 TO 3
    FOR J = 1 TO 4
        BEGIN CASE
        CASE J = 2
            EXIT
        CASE 1
            PRINT I : '.' : J
        END CASE
    NEXT J
    IF I = 2 THEN EXIT
NEXT I
PRINT 'counters ' : I : ',' : J
N = 0
LOOP
    N += 1
    IF N = 2 THEN EXIT
    PRINT 'loop ' : N
WHILE N < 4 DO
REPEAT
PRINT 'after ' : N
EXIT(0)
PRINT 'unreachable'
