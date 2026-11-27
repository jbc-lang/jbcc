* tafc-emulation: jbase
* TAFC-CROSSCHECK.md section 1: LOCATE coordinates, separate start and the function form.
A = 'a':@FM:'b':@VM:'x':@VM:'y':@SM:'s1':@SM:'s2':@FM:'e':@FM:'x'
LOCATE 'x' IN A<2>, 1 SETTING P THEN CRT '1 found ':P ELSE CRT '1 not ':P
LOCATE 'x' IN A<1>, 3 SETTING P THEN CRT '2 found ':P ELSE CRT '2 not ':P
LOCATE 'y' IN A<2,1>, 3 SETTING P THEN CRT '3 found ':P ELSE CRT '3 not ':P
LOCATE 's2' IN A<2,3,1> SETTING P THEN CRT '4 found ':P ELSE CRT '4 not ':P
LOCATE 's2' IN A<2,3,2> SETTING P THEN CRT '5 found ':P ELSE CRT '5 not ':P
LOCATE 'x' IN A<4> SETTING P THEN CRT '6 found ':P ELSE CRT '6 not ':P
LOCATE 'x' IN A<5> SETTING P THEN CRT '7 found ':P ELSE CRT '7 not ':P
LOCATE 'y' IN A<2,3> SETTING P THEN CRT '8 found ':P ELSE CRT '8 not ':P
LOCATE('x', A; P) THEN CRT '9 found ':P ELSE CRT '9 not ':P
LOCATE('x', A, 2; P) THEN CRT '10 found ':P ELSE CRT '10 not ':P
LOCATE('s2', A, 2, 3; P) THEN CRT '11 found ':P ELSE CRT '11 not ':P
LOCATE('c', 'a':@FM:'b':@FM:'d'; P; 'AL') THEN CRT '12 found ':P ELSE CRT '12 not ':P
LOCATE('c', 'a':@VM:'b':@VM:'d', 1; P; 'AL') THEN CRT '13 found ':P ELSE CRT '13 not ':P
LOCATE '' IN A<1> SETTING P THEN CRT '14 found ':P ELSE CRT '14 not ':P
LOCATE '' IN '' SETTING P THEN CRT '15 found ':P ELSE CRT '15 not ':P
LOCATE 'x' IN A<1> BY 'AL' SETTING P THEN CRT '16 found ':P ELSE CRT '16 not ':P
LOCATE 'b' IN A<2> BY 'AL' SETTING P THEN CRT '17 found ':P ELSE CRT '17 not ':P
LOCATE 'b' IN A<2,1> BY 'AL' SETTING P THEN CRT '18 found ':P ELSE CRT '18 not ':P
B = 'a':@VM:'c':@FM:'b'
LOCATE 'b' IN B<1,1> BY 'AL' SETTING P THEN CRT '19 found ':P ELSE CRT '19 not ':P
LOCATE 'b' IN B<1> BY 'AL' SETTING P THEN CRT '20 found ':P ELSE CRT '20 not ':P
LOCATE 'a' IN A<1>, 2 SETTING P THEN CRT 's1 found ':P ELSE CRT 's1 not ':P
LOCATE 'a' IN A<2>, 1 SETTING P THEN CRT 's2 found ':P ELSE CRT 's2 not ':P
LOCATE 'a' IN A, 2 SETTING P THEN CRT 's3 found ':P ELSE CRT 's3 not ':P
LOCATE 'b' IN A<2,2>, 1 SETTING P THEN CRT 's4 found ':P ELSE CRT 's4 not ':P
LOCATE 'x' IN A<2,1>, 2 SETTING P THEN CRT 's5 found ':P ELSE CRT 's5 not ':P
LOCATE 'a' IN A<0> SETTING P THEN CRT 's6 found ':P ELSE CRT 's6 not ':P
LOCATE 'b' IN A<2,0> SETTING P THEN CRT 's7 found ':P ELSE CRT 's7 not ':P
