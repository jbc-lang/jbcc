* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: CHAR modulo 256 and embedded NUL.
CRT OCONV(CHAR(256), 'MX'), OCONV(CHAR(300), 'MX'), OCONV(CHAR(-1), 'MX')
CRT OCONV(CHAR(0):'A', 'MX'), LEN(CHAR(0):'A'), SEQ(CHAR(0)), SEQ('')
