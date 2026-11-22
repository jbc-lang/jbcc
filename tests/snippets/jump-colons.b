GOTO start:
CRT "unexpected"
10: CRT "numeric subroutine"; RETURN
start:
GOSUB 10:; GOSUB report:
GOTO 20 :
report: CRT "named subroutine"; RETURN
20: CRT "done"
