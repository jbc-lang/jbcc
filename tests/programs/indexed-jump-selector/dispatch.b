DEFFUN PICK(N)
N = 1
ON PICK(N) GOSUB first, second
CRT N
STOP
first: CRT 'first'; RETURN
second: CRT 'second'; RETURN
