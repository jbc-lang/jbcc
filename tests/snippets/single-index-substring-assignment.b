Text = 'abcde'
Text[2.9] = 'WXYZ'
CRT Text
Text[3] = ''
CRT Text
Text[0] = '!'
Text[-1] := '?'
CRT Text
Text[999] = 'whole'
CRT Text
DIM A(2)
A(1) = 'left'
A(2) = 'right'
A(1)[1] = 'T'
A(2)[2] := '!'
CRT A(1):':':A(2)
R = 'one':@FM:'two'
R<2>[2] = 'WO'
CRT R<1>:':':R<2>
