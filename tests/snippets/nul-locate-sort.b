* Byte 0 is an ordinary byte for LOCATE, SORT and CONVERT. TAFC PB201214
* finds no value that holds it, scrambles SORT and empties CONVERT
* (LANGUAGE-GAPS.md); jbcc keeps every byte.
Z = CHAR(0)
A = 'c':Z:@VM:Z:'d'
LOCATE 'c':Z IN A<1,1> SETTING P THEN CRT 'found ':P ELSE CRT 'missing ':P
LOCATE Z:'d' IN A<1,1> SETTING P THEN CRT 'found ':P ELSE CRT 'missing ':P
LOCATE 'c' IN A<1,1> SETTING P THEN CRT 'found ':P ELSE CRT 'missing ':P
CRT OCONV(SORT('b':@FM:Z:'a':@FM:'a'), 'MX')
CRT OCONV(CONVERT('a', Z, 'a':Z:'b'), 'MX')
