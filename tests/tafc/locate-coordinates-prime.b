* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 1: LOCATE IN A<f> searches fields under prime.
A = 'a':@FM:'c':@VM:'x':@FM:'e'
LOCATE 'c' IN A<1> SETTING P THEN CRT 'c found ':P ELSE CRT 'c not ':P
LOCATE 'e' IN A<1> SETTING P THEN CRT 'e found ':P ELSE CRT 'e not ':P
LOCATE 'e' IN A<2> SETTING P THEN CRT 'e from 2 found ':P ELSE CRT 'e from 2 not ':P
LOCATE 'x' IN A<2,1> SETTING P THEN CRT 'x found ':P ELSE CRT 'x not ':P
LOCATE 'e' IN A SETTING P THEN CRT 'plain found ':P ELSE CRT 'plain not ':P
LOCATE 'b' IN A<1> BY 'AL' SETTING P ELSE CRT 'b by AL ':P
