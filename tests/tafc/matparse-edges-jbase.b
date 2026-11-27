* tafc-emulation: jbase
* TAFC-CROSSCHECK.md: MATPARSE trailing delimiters, USING '' and ranges.
DIM M(4)
MATPARSE M FROM '':@FM:'b' SETTING N ; CRT 1:' ':N
MATPARSE M FROM 'a':@FM:'':@FM:'b' SETTING N ; CRT 2:' ':N
MATPARSE M FROM 'a':@FM:@FM SETTING N ; CRT 3:' ':N
MATPARSE M FROM @FM SETTING N ; CRT 4:' ':N
MATPARSE M FROM 'a':@FM:'b':@FM:'c':@FM:'' SETTING N ; CRT 5:' ':N
MATPARSE M FROM 'a':@FM:'b':@FM:'c':@FM:'':@FM:'' SETTING N ; CRT 6:' ':N:' [':M(4):']'
MATPARSE M FROM 'a':@FM:'b':@FM:'c':@FM:'d':@FM:'' SETTING N ; CRT 7:' ':N:' [':M(4):']'
MAT M = 'z'
MATPARSE M FROM 'a':@FM:'b' SETTING N ; CRT 8:' ':N:' [':M(3):'][':M(4):']'
MATPARSE M FROM 'a b c' USING ' ' SETTING N ; CRT 9:' ':N
MATPARSE M FROM 'a  b' USING ' ' SETTING N ; CRT 10:' ':N:' [':M(2):']'
MATPARSE M FROM 'abc' USING '' SETTING N ; CRT 11:' ':N:' [':M(1):']'
MATPARSE M, 2, 3 FROM 'a':@FM:'b':@FM:'c' SETTING N ; CRT 12:' ':N:' [':M(1):'][':M(2):'][':M(3):']'
