* tafc-emulation: prime
* TAFC-CROSSCHECK.md: EXECUTE PASSDATA and RTNDATA with COLLECTDATA and RTNDATA.
X = 'hello':@FM:'world':@VM:'v'
Y = 'untouched'
EXECUTE './CHILD' PASSDATA X RTNDATA Y
CRT 'back [':Y:']'
Y = 'untouched'
EXECUTE './QUIET' PASSDATA X RTNDATA Y
CRT 'quiet [':Y:']'
EXECUTE './CHILD' RTNDATA Y
CRT 'no passdata [':Y:']'
EXECUTE './CHILD' PASSDATA 'literal'
EXECUTE './CHILD' PASSDATA X CAPTURING C RTNDATA Y
CRT 'captured [':C:'] [':Y:']'
EXECUTE './GRAND' PASSDATA 'outer' RTNDATA Y
CRT 'grand [':Y:']'
COLLECTDATA Z
CRT 'parent collect [':Z:']'
RTNDATA 'nobody'
CRT 'done'
* tafc-program: CHILD
COLLECTDATA A
CRT 'child got [':A:']'
COLLECTDATA B
CRT 'child again [':B:']'
RTNDATA 'first'
RTNDATA 'back':@VM:A<2>
* tafc-program: QUIET
COLLECTDATA A
CRT 'quiet got ':DCOUNT(A, @FM)
* tafc-program: GRAND
COLLECTDATA A
CRT 'grand got [':A:']'
EXECUTE './CHILD'
EXECUTE './CHILD' RTNDATA R
CRT 'grand inner [':R:']'
RTNDATA 'from grand'
