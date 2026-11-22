PROGRAM = 4
PROGRAM +   = 2
PROGRAM *= 3
PROGRAM / = 4
CRT PROGRAM
R = 3 : @FM : 12
R<1> + = 1
R<2> -	= 2
R<2> * = R<1>
CRT R<1> : ',' : R<2>
DIM M(2)
M(2) = 9
M(2) /= 2
CRT M(2)
READV = 12
READV * = 3
CRT READV
done:* = comment after label
CRT '+ = : = *='
