INPUT Ready, -1
CRT Ready
LOOP
    INPUT Ready, -1
UNTIL Ready DO
    SLEEP .01
REPEAT
CRT Ready, KEYIN()
