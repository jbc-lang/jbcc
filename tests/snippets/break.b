BREAK = 'after'
N = 0
FOR I = 1 TO 3
    N = 0
    LOOP
        N += 1
        IF N = 2 THEN BREAK
        CRT I : '.' : N
    REPEAT
    IF I = 2 THEN BREAK
NEXT I
CRT BREAK : ' ' : I : '.' : N
