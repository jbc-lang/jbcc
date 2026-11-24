I = 0
Limit = 0
ON 2 GO TO safe, middle
FOR I = 99 TO Limit
middle: PRINT I
Limit = 2
NEXT I
safe: STOP
