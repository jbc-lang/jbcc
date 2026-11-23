V = IF 1 THEN 'yes' ELSE (1 / 0)
CRT V
CRT IF 0 THEN 1 / 0 ELSE 'no'
CRT IF 1 THEN 2 ELSE 3 + 10
CRT IF 0 THEN 2 ELSE (3 + 10)
CRT IF 1 THEN 2 ELSE 3 ^ 2
CRT 'prefix:':(IF 0 THEN 'wrong' ELSE 'right'):':suffix'
CRT LEN(IF 0 THEN 'a' ELSE 'long')
R = 'first':@FM:'second'
CRT R<(IF 0 THEN 1 ELSE 2)>
R <(IF 1 THEN 1 ELSE 2)>='changed'
CRT R<1>
CRT IF 1 THEN IF 0 THEN 'wrong' ELSE 'inner else' ELSE 'outer else'
IF IF 0 THEN 0 ELSE 1 THEN CRT 'statement then' ELSE STOP
IF ASSIGNED(X) THEN STOP
CRT IF UNASSIGNED(X) THEN 'unassigned' ELSE X
