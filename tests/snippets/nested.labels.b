N = 0
GOTO repeat.here
LOOP
  N += 1
  IF N EQ 2 THEN GOTO finished
  PRINT N
  repeat.here:
REPEAT
finished:
GOSUB report
IF 0 THEN
  report: PRINT 'report'
  RETURN
END
S = 1
FOR I = 1 TO 5 STEP S + 1
  FOR J = 1 TO 2
    Junk = 'temporary' : J
    GOTO advance
  NEXT J
  advance: PRINT I
NEXT I
GOTO otherwise
BEGIN CASE
CASE 0
  PRINT 'wrong'
CASE 0
  otherwise: PRINT 'case'
END CASE
