OPEN 'F' TO F ELSE STOP
OPEN 'F' ELSE STOP
READU V FROM 'new' ELSE NULL
WRITE 'inserted' ON F,'new' SETTING S ON ERROR ABORT 'unexpected'
CRT LEN(S), RECORDLOCKED(F,'new')
READ V FROM F,'new' THEN CRT V ELSE STOP
WRITE 'updated' TO 'new' THEN CRT 'then' ELSE ABORT 'unexpected'
WRITE 'blocked' TO 'busy' ELSE CRT 'else'
DIM Codes(1)
WRITE 'blocked' TO F,'busy' SETTING Codes(1) ON ERROR
  CRT Codes(1), RECORDLOCKED(F,'busy')
END
READ V FROM 'busy' THEN ABORT 'unexpected' ELSE CRT 'no record'
Bad = 'F'
WRITE 'lost' ON Bad,'new' SETTING S ON ERROR CRT 'bad ':S
WRITE 'lost' TO Bad,'new' SETTING S
CRT S
READ V FROM 'new' THEN CRT V ELSE STOP
