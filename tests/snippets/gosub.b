GOSUB increment.twice
CRT N
STOP
increment.twice:
N = 2
GOSUB increment
GOSUB increment
RETURN
increment:
N += 1
RETURN
