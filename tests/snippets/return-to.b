GOSUB outer
CRT "main"
FOR I = 1 TO 2 STEP 1
    GOSUB redirect
    CRT "unexpected"
again: CRT I
NEXT I
STOP
outer:
GOSUB inner
CRT "unexpected"
resume: CRT "outer"
RETURN
inner:
RETURN TO resume:
redirect:
RETURN TO again
