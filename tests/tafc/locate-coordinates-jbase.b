* tafc-emulation: jbase
* TAFC-CROSSCHECK.md section 1: LOCATE IN A<f> searches values under jbase.
A = 'a':@FM:'c':@VM:'x':@FM:'e'
LOCATE 'c' IN A<1> SETTING P THEN CRT 'c found ':P ELSE CRT 'c not ':P
LOCATE 'x' IN A<2> SETTING P THEN CRT 'x found ':P ELSE CRT 'x not ':P
LOCATE 'x' IN A<2,1> SETTING P THEN CRT 'x 2,1 found ':P ELSE CRT 'x 2,1 not ':P
LOCATE 'e' IN A SETTING P THEN CRT 'plain found ':P ELSE CRT 'plain not ':P
