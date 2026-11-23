FORMLIST 'first':@FM:'stop':@FM:'last'
LOOP READNEXT K THEN IF K = 'stop' THEN K = '' ELSE CRT 'got ':K ELSE CRT 'exhausted' WHILE K <> '' DO
  CRT 'body ':K
REPEAT
READNEXT K THEN CRT 'left ':K
FORMLIST 'another'
LOOP READNEXT K ELSE K = 'done' UNTIL K = 'done'
  CRT K
REPEAT
CRT K
I = 0
LOOP
  I += 1
  IF I = 1 THEN WHILE = 'variable' UNTIL I = 2
REPEAT
CRT 'iterations ':I
LOOP IF 1 THEN EXIT REPEAT
