* tafc-emulation: prime
* TAFC-CROSSCHECK.md: EXECUTE PASSLIST and RTNLIST.
L = 'a':@FM:'b':@FM:'c'
R = 'untouched'
EXECUTE './CHILD' PASSLIST L RTNLIST R
CRT 'rtnlist [':CHANGE(R, @FM, '|'):']'
EXECUTE './CHILD'
R = 'untouched'
EXECUTE './QUIET' RTNLIST R
CRT 'quiet [':CHANGE(R, @FM, '|'):'] ':ASSIGNED(R)
P = 'p':@FM:'q' ; SELECT P
EXECUTE './CHILD' PASSLIST
READNEXT K THEN CRT 'parent default still has ':K ELSE CRT 'parent default empty'
EXECUTE './CHILD' RTNLIST
N = 0
LOOP WHILE READNEXT K DO N += 1 ; CRT 'parent next ':K REPEAT
CRT 'parent read ':N
EXECUTE './PARTIAL' PASSLIST L RTNLIST R
CRT 'partial [':CHANGE(R, @FM, '|'):']'
* tafc-program: CHILD
N = 0
LOOP WHILE READNEXT K DO N += 1 ; CRT 'child next ':K REPEAT
CRT 'child read ':N
X = 'x':@FM:'y'
SELECT X
* tafc-program: QUIET
CRT 'quiet child'
* tafc-program: PARTIAL
READNEXT K ELSE NULL
CRT 'partial took ':K
