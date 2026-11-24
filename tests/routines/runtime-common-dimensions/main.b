CFG<1> = 2
COMMON /CACHE/ Head, Rows(CFG<1>, 1), Tail, More(CFG<1> + 1)
CFG<1> = 8
Head = 'head'
Tail = 'tail'
MAT Rows = 'row'
Rows(2,1) = 'edge'
MAT More = 'extra'
CALL CHANGE()
PRINT Head, Rows(0,0), Rows(2,1), Tail, More(3)
