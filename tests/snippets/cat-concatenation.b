GOTO CAT
CRT 'unexpected'
CAT:
R = 'first':@FM:'second'
Text = R <2> CAT 1 + 2 : '!'
CRT Text
CRT 'a' CAT CAT 'b'
DISPLAY ('c' CAT)
PRINT 'd' CAT
CRT 'e'
CRT 'f' CAT 'g'
