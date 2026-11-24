ON 0 GOSUB low, high
ON '999999999999999999999' GOTO low, high
CRT 'fell through'
STOP
low: CRT 'low'; RETURN
high: CRT 'high'; STOP
