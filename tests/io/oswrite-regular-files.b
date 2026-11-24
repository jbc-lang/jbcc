OSWRITE 'new':CHAR(128) TO 'payload' SETTING S
CRT S:':':STATUS()
OSWRITE CHAR(10):'tail' APPEND ON 'payload'
OSREAD B FROM 'payload' THEN CRT B ELSE ABORT
OSWRITE 'created' TO 'new'
OSWRITE '' TO 'empty'
