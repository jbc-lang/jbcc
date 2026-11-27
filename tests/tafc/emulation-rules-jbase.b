* tafc-emulation: jbase
* TAFC-CROSSCHECK.md: NUM, COUNT, MATPARSE, ABSS and NEGS under jbase.
FOR I = 1 TO 11
   V = FIELD('|.|+|-| 12|12 |1,2|1E3|0012|-1.5|abc', '|', I)
   CRT I:' [':V:'] ':NUM(V)
NEXT I
CRT NUMS('1':@VM:'':@VM:'x':@FM:' 3')
CRT COUNT('aaaa', 'aa'), COUNT('abc', ''), COUNT('', 'a'), COUNT('', '')
CRT COUNTS('aaa':@VM:'':@VM:'ba', 'a')
DIM M(4)
MATPARSE M FROM 'a':@FM:'b':@FM:'c' SETTING N
CRT N:' [':M(1):'][':M(2):'][':M(3):'][':M(4):']'
MATPARSE M FROM 'a':@FM:'b':@FM:'c':@FM:'d':@FM:'e' SETTING N
CRT N:' [':M(4):']'
MATPARSE M FROM '' SETTING N
CRT N:' [':M(1):']'
MATPARSE M FROM 'x|y' USING '|' SETTING N
CRT N:' [':M(1):'][':M(2):']'
CRT CHANGE(ABSS('-1':@VM:'':@VM:'2'), @VM, ',')
CRT CHANGE(NEGS('-1':@VM:'':@VM:'2'), @VM, ',')
* Second round.
FOR I = 1 TO 14
   V = FIELD('+5|-.5|5.| |  |1 2|  7  |+ 5|- 5|0x1|.5.|--5|1-|+', '|', I)
   CRT I:' [':V:'] ':NUM(V)
NEXT I
V = CHAR(9):'5' ; CRT 'tab ':NUM(V)
CRT COUNTS('aaaa':@VM:'abab', 'aa'), COUNTS('aaaa', '')
CRT COUNT('aaaa':@VM:'aa', 'aa'), COUNT('ababab', 'aba'), DCOUNT('aaaa', 'aa')
DIM P(3)
MATPARSE P FROM 'a':@FM:'b':@FM:'c':@FM:'d' SETTING N
CRT N:' [':P(3):']'
MATPARSE P FROM 'a':@FM:'b':@FM:'c' SETTING N
CRT N:' [':P(3):']'
MATPARSE P FROM 'a':@FM:'b' SETTING N
CRT N:' [':P(2):'][':P(3):']'
MATPARSE P FROM 'a':@FM:'' SETTING N
CRT N:' [':P(2):']'
MATPARSE P FROM 'a':@FM:'b':@VM:'c':@FM:'d':@FM:'e' SETTING N
CRT N:' [':P(3):']'
CRT CHANGE(ABSS(''), @VM, ','):'|':CHANGE(NEGS('':@VM:''), @VM, ',')
