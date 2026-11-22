GO init
show: CRT Value
ON 2 GO TO bad, 100
bad: CRT 'wrong'
STOP
init: Value = 'ready'
IF 1 THEN GO TO show:
100: ON 1 GO finish, bad
finish: CRT 'done'
