N = 0
Old = N++
New = ++N
CRT Old:':':New:':':N
CRT N--:':':--N:':':N
N = 4
CRT N - N++
CRT N++ + N++ * 2
IF 0 AND ++N THEN ABORT
V = IF 1 THEN N ELSE N++
CRT V:':':N
DIM A(2)
A(1) = 8
A(2) = 20
I = 1
CRT A(I++)++:':':I:':':A(1)
CALL SHOW.STEPS(A(2)--, --A(2), A(2))
