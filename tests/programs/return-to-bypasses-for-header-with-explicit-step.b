I = 0
GOSUB redirect
FOR I = 99 TO 2 STEP 2
middle: CRT I
NEXT I
STOP
redirect: RETURN TO middle
