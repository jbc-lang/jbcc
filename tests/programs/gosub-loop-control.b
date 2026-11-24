FOR I = 1 TO 2
    GOSUB Work
    CRT 'caller ':I
NEXT I
STOP
Work:
    IF I = 1 THEN CONTINUE
    IF I = 2 THEN
        EXIT
    END
    CRT 'body ':I
    RETURN
