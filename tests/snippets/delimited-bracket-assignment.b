Text = 'a--b--c--d'
CRT Text['--',2,2]
Text['--',2,2] = 'new'
CRT Text
Text['--',2,1] := '!'
CRT Text
Text['--',2,1] = ''
CRT Text
Text['--',5,1] = 'end'
CRT Text
Empty['.',3,1] = 'x'
CRT Empty
Empty['.',2,9] = 'rest'
CRT Empty
DIM Rows(2)
Rows(1) = 'left/right':@FM:'keep'
Rows(1)<1>['/',2,1] = 'changed'
CRT Rows(1)
CRT COL1():':':COL2()
Text['',1,1] = 'whole'
CRT Text
