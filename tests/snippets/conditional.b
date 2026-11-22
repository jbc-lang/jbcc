X = "02"
IF X EQ 2 THEN
  IF 1 THEN RESULT = 'taken' ELSE RESULT = 'wrong'
END ELSE
  RESULT = 'other'
END
CRT RESULT
IF X LT 1 THEN RESULT = 'wrong' ELSE RESULT = 'other'
CRT RESULT
IF "-0.00" THEN CRT "wrong" ELSE CRT "zero"
IF "" ELSE CRT "empty"
IF "YES" THEN CRT "text"
IF 0 THEN CRT "invalid" + 1
CRT 1 LE 1
CRT 3 GT 2
CRT 0 GE 1
CRT "A" NE "B"
