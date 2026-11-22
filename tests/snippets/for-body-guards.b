FOR I = 1 TO 5
    CRT 'early ' : I
UNTIL I = 2
NEXT I
CRT 'stopped ' : I
FOR J = 3 TO 1 STEP -1
    IF J = 3 THEN CONTINUE
    UNTIL J = 3
    WHILE J > 0 DO CRT 'body ' : J
NEXT J
CRT 'finished ' : J
FOR K = 2 TO 1
    UNTIL 1 / 0
NEXT K
FOR N = 1 TO 4
    UNTIL = N
    WHILE UNTIL < 3
    CRT 'name ' : (UNTIL)
NEXT N
FOR A = 1 TO 3
    FOR B = 1 TO 4
        UNTIL B = A
    NEXT B
    CRT A : ',' : B
    UNTIL A = 2
NEXT A
