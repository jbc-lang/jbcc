* tafc-emulation: prime
* PLAN.md: ENCRYPT and DECRYPT with JBASE_CRYPT_BASE64 (4) and XOR11 (2).
FOR I = 1 TO 6
   T = FIELD(',a,ab,abc,abcd,hello world', ',', I)
   CRT I:' [':ENCRYPT(T, '', 4):']'
NEXT I
L = STR('0123456789', 10)
E = ENCRYPT(L, '', 4)
CRT 7:' ':LEN(E):' ':OCONV(E[57, 30], 'MX')
CRT 8:' ':(DECRYPT(E, '', 4) = L)
CRT 9:' [':ENCRYPT(CHAR(0):CHAR(255):@FM, 'key', 4):']'
CRT 10:' ':OCONV(DECRYPT('AP/+', '', 4), 'MX')
CRT 11:' [':DECRYPT('aGVsbG8=', '', 4):'] [':DECRYPT('aGVsbG8', '', 4):'] [':DECRYPT('aGVs bG8=', '', 4):']'
CRT 12:' ':OCONV(DECRYPT('!!!!', '', 4), 'MX'):' ':OCONV(DECRYPT('aGVsbG8=junk', '', 4), 'MX')
CRT 13:' ':OCONV(DECRYPT('YQ==YQ==', '', 4), 'MX'):' ':OCONV(DECRYPT('YQ', '', 4), 'MX'):' ':OCONV(DECRYPT('Y', '', 4), 'MX')
CRT 14:' ':OCONV(DECRYPT('aGVs':CHAR(10):'bG8=', '', 4), 'MX'):' ':OCONV(DECRYPT('-_8', '', 4), 'MX')
CRT 15:' ':OCONV(ENCRYPT('abc', 'k', 2), 'MX'):' ':OCONV(ENCRYPT('abc', 'K', 2), 'MX'):' ':OCONV(ENCRYPT('hello', 'k', 2), 'MX')
CRT 16:' ':OCONV(ENCRYPT('abc', '', 2), 'MX'):' ':OCONV(ENCRYPT('aaaa', 'a', 2), 'MX'):' ':OCONV(DECRYPT(ENCRYPT('hello', 'k', 2), 'k', 2), 'MX')
A = STR('a', 300)
X = ENCRYPT(A, 'k', 2)
CRT 17:' ':OCONV(X[1, 4], 'MX'):' ':OCONV(X[240, 20], 'MX'):' ':OCONV(X[296, 5], 'MX')
CRT 18:' ':OCONV(ENCRYPT('abc', 'kz', 2), 'MX'):' ':(DECRYPT(X, 'k', 2) = A):' ':OCONV(ENCRYPT('abc', CHAR(200), 2), 'MX')
CRT 19:' ':OCONV(ENCRYPT('abc', '7', 2), 'MX'):' ':OCONV(ENCRYPT(@FM:CHAR(0), 'k', 2), 'MX')
M = BITOR(2, XTD('40000000'))
CRT 20:' [':ENCRYPT('hello', 'k', M):'] [':DECRYPT(ENCRYPT('hello', 'k', M), 'k', M):'] [':ENCRYPT('hello', '', BITOR(1, XTD('40000000'))):']'
CRT 21:' [':ENCRYPT('hello', '', BITOR(4, XTD('40000000'))):']'
