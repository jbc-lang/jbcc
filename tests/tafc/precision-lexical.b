* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 2: the first PRECISION covers earlier lines.
CRT 'a ':10/3
IF 0 THEN PRECISION 6
CRT 'b ':10/3
GOSUB SHOW
PRECISION 2
CRT 'c ':10/3
GOSUB SHOW
STOP
SHOW:
CRT 's ':10/3
RETURN
