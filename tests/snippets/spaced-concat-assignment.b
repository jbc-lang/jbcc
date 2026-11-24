Text = 'a'
add: Text : = 'b'
IF Text = 'ab' THEN Text :	= 'c' ELSE ABORT
PROGRAM = 'p'
PROGRAM : = 'q'
R = 'first':@FM:'second'
R<2> : = '!'
DIM A(1)
A(1) = 'left'
A(1)[1] : = '+'
CRT Text:':':PROGRAM:':':R<2>:':':A(1)
CRT ('a' : 'b') = 'ab'
CRT ': ='
