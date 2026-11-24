SUBROUTINE CHECK()
GOSUB outer
CRT "unexpected"
RETURN
outer: GOSUB aborting
CRT "unexpected"
RETURN
aborting: CRT "unwind"
RETURN TO aborting
