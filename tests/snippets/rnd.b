CRT RND(1)
CRT RND('-0001.00')
FOR I = 1 TO 100
    A = RND(26)
    B = RND(-99)
    C = RND(2147483647)
    IF A < 0 OR A >= 26 OR A # INT(A) THEN CRT 'out of range'
    IF B < 0 OR B >= 99 OR B # INT(B) THEN CRT 'out of range'
    IF C < 0 OR C >= 2147483647 OR C # INT(C) THEN CRT 'out of range'
NEXT I
CRT 'in range'
