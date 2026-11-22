Stride = 1
FOR I = 1 TO 6 STEP Stride
  BEGIN CASE
    CASE I = 1
      Stride = 2
      CONTINUE
  END CASE
  N = 0
  LOOP
    N += 1
    IF N = 2 THEN CONTINUE
  UNTIL N > 3 DO
    PRINT I : '.' : N
  REPEAT
  IF I = 4 THEN CONTINUE
  PRINT 'end ' : I
NEXT I
PRINT 'after ' : I
