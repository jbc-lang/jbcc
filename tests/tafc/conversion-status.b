* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 5: invalid masks and STATUS().
X = OCONV('abc', 'QWERTY') ; CRT 'oconv bad [':X:'] ':STATUS()
X = ICONV('abc', 'QWERTY') ; CRT 'iconv bad [':X:'] ':STATUS()
X = OCONV('abc', 'D') ; CRT 'D text [':X:'] ':STATUS()
X = ICONV('31 FEB 2020', 'D') ; CRT 'feb 31 [':X:'] ':STATUS()
X = ICONV('12:99', 'MT') ; CRT 'bad time [':X:'] ':STATUS()
X = ICONV('abc', 'MD2') ; CRT 'iconv MD2 [':X:'] ':STATUS()
X = OCONV('abc', 'MD2') ; CRT 'oconv MD2 [':X:'] ':STATUS()
X = OCONV('1', 'D') ; CRT 'good [':X:'] ':STATUS()
