* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: @ variables, checked against DATE().
D = DATE()
CRT (@DAY = OCONV(D, 'DD') + 0), (@MONTH = OCONV(D, 'DM') + 0), (@YEAR = OCONV(D, 'DY2'))
CRT (@UID = '' : @UID + 0), @LEVEL, '[':@DATA:']', OCONV(@EOF, 'MX')
CRT '[':@CODEPAGE:'] [':@LOCALE:'] [':@USER.THREAD:'] [':@CALLSTACK:']'
