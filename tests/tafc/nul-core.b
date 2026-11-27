* tafc-emulation: prime
* NUL-BYTES.md stage 2: byte 0 in CHAR, concatenation, LEN, substrings,
* comparisons, output and the MX and MCP conversions.
Z = CHAR(0)
X = 'A':Z:'B'
CRT 1:' ':LEN(Z):' ':SEQ(Z):' ':OCONV(Z, 'MX'):' ':OCONV(CHAR(256):Z, 'MX')
CRT 2:' ':LEN(X):' ':OCONV(X, 'MX'):' ':OCONV(X:1, 'MX'):' ':OCONV(Z:Z, 'MX')
CRT 3:' ':OCONV(X[2,2], 'MX'):' ':OCONV(X[3,1], 'MX'):' ':LEN(X[1,2]):' ':OCONV(X[-2,2], 'MX')
CRT 4:' ':OCONV(LEFT(X, 2), 'MX'):' ':OCONV(RIGHT(X, 2), 'MX')
W = 'A':CHAR(1)
CRT 5:' ':(X = 'A'):(X = 'A':Z:'B'):(X GT 'A'):('A' LT X):(X LT W):(Z = ''):(Z GT '')
IF X = 'A' THEN CRT 6:' equal' ELSE CRT 6:' different'
Y = X ; Y[2,1] = 'z' ; CRT 7:' ':Y
Y = 'abc' ; Y[2,1] = Z ; CRT 8:' ':OCONV(Y, 'MX'):' ':LEN(Y)
CRT 9:' ':OCONV(ICONV('410042', 'MX'), 'MX'):' ':LEN(ICONV('0000', 'MX'))
CRT 10:' ':OCONV(X, 'MCP'):' ':OCONV(X, 'MCPN'):' ':OCONV(OCONV('A.00B', 'MCNP'), 'MX')
CRT 11:' [':X:']'
CRT 12:' ':OCONV(CHARS(0:@VM:65), 'MX'):' ':LEN(STR(Z, 3)):' ':OCONV(DOWNCASE(X), 'MX')
CRT 13:' ':OCONV(TRIM(' ':Z:' '), 'MX'):' ':OCONV(X:@FM:Z, 'MX')
CRT 14:' ':CHECKSUM(Z:'!'):' ':CHECKSUM('a':Z:'b')
