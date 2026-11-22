N = 3; EQU K TO N; CRT K; EQUATE K TO 7; CRT K
EQU A TO 1; EQU B TO 2,
    C TO 3; CRT A : B : C
EQU TEXT TO REPLACE('one;two',1;'new;value'); CRT TEXT
EQU FLAG TO 1; IF FLAG THEN CRT 'yes'; EQU FLAG TO 0
IF FLAG THEN CRT 'wrong' ELSE CRT 'no'
CRT K; EQU K TO 8; * updated for the next line
CRT K
N = 1; EQU = N + 1; CRT EQU
