* tafc-emulation: prime
* NUL-BYTES.md stage 3: byte 0 in dynamic arrays and the search functions.
* TAFC's LOCATE, SORT and CONVERT to byte 0 mishandle it; LANGUAGE-GAPS.md.
Z = CHAR(0)
A = 'a':Z:'b':@FM:'c':Z:@VM:Z:'d'
CRT 1:' ':OCONV(A<1>, 'MX'):' ':OCONV(A<2,1>, 'MX'):' ':OCONV(A<2,2>, 'MX'):' ':DCOUNT(A, @FM)
B = A ; B<3> = 'x':Z ; CRT 2:' ':OCONV(B, 'MX')
B = A ; B = INSERT(B, 2, 1; Z) ; CRT 3:' ':OCONV(B, 'MX')
B = A ; B = DELETE(B, 1) ; CRT 4:' ':OCONV(B, 'MX')
B = A ; B = REPLACE(B, 2, 2; 'y':Z) ; CRT 5:' ':OCONV(B, 'MX')
CRT 6:' ':OCONV(FIELD('a':Z:'b,c', ',', 1), 'MX'):' ':OCONV(FIELD('a,b':Z:'c', ',', 2), 'MX'):' ':OCONV(FIELD('a':Z:'b':Z:'c', Z, 2), 'MX')
CRT 7:' ':INDEX('a':Z:'b', 'b', 1):' ':INDEX('a':Z:'b', Z, 1):' ':INDEX(Z:Z, Z, 2):' ':COUNT('a':Z:Z:'b', Z):' ':DCOUNT('a':Z:'b', Z)
CRT 8:' ':OCONV(CHANGE('a':Z:'b', Z, '-'), 'MX'):' ':OCONV(CHANGE('a-b', '-', Z), 'MX'):' ':OCONV(EREPLACE('a':Z:'b', 'b', 'c'), 'MX')
CRT 9:' ':OCONV(CONVERT(Z, 'x', 'a':Z:'b'), 'MX')
CRT 12:' ':OCONV(A<2>, 'MX'):' ':LEN(A<2>):' ':OCONV(EXTRACT(A, 2, 2), 'MX')
CRT 13:' ':OCONV(LOWER(A), 'MX'):' ':OCONV(RAISE(Z:@VM:Z), 'MX')
CRT 14:' ':OCONV(LENS('a':Z:@VM:Z), 'MX'):' ':OCONV(FIELDS('a':Z:'b':@VM:'c,d', ',', 1), 'MX')
CRT 15:' ':OCONV(SPLICE('a':@VM:Z, Z, 'b':@VM:'c'), 'MX'):' ':OCONV(CATS(Z:@VM:'a', 'b':@VM:Z), 'MX')
CRT 16:' ':OCONV(GROUP('a':Z:'b-c', '-', 1), 'MX')
REMOVE R FROM A SETTING D ; CRT 17:' ':OCONV(R, 'MX'):' ':D
CRT 18:' ':OCONV(TRIM(Z:'  ':Z, ' ', 'R'), 'MX'):' ':OCONV(SWAP('a':Z:'b', Z, 'x'), 'MX')
