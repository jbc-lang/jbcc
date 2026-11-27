* tafc-emulation: prime
* TAFC-CROSSCHECK.md: masks chained with value marks, and STATUS().
* Each case runs from STATUS() 0 and from STATUS() 3.
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'MCU') ; S0 = STATUS()
CRT 1:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('12', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('12', 'MD2') ; S0 = STATUS()
CRT 2:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'MD2') ; S0 = STATUS()
CRT 3:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('1', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('1', 'D') ; S0 = STATUS()
CRT 4:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'D') ; S0 = STATUS()
CRT 5:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'QWERTY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'QWERTY') ; S0 = STATUS()
CRT 6:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(3600, 'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(3600, 'MTS') ; S0 = STATUS()
CRT 7:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('x', 'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('x', 'MTS') ; S0 = STATUS()
CRT 8:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'MX') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'MX') ; S0 = STATUS()
CRT 9:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'G0 1') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'G0 1') ; S0 = STATUS()
CRT 10:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('100':@VM:'200', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('100':@VM:'200', 'MD2') ; S0 = STATUS()
CRT 11:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('1':@VM:'2', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('1':@VM:'2', 'MD2') ; S0 = STATUS()
CRT 12:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('1':@VM:'x', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('1':@VM:'x', 'D') ; S0 = STATUS()
CRT 13:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('1':@VM:'2', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('1':@VM:'2', 'D') ; S0 = STATUS()
CRT 14:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('', 'MD2') ; S0 = STATUS()
CRT 15:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('1':@VM:'2', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('1':@VM:'2', 'MD2') ; S0 = STATUS()
CRT 16:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('1':@VM:'x', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('1':@VM:'x', 'MD2') ; S0 = STATUS()
CRT 17:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('01/31/2020':@VM:'bad', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('01/31/2020':@VM:'bad', 'D') ; S0 = STATUS()
CRT 18:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('', 'D') ; S0 = STATUS()
CRT 19:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('', 'MD2') ; S0 = STATUS()
CRT 20:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('1':@VM:'2', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('1':@VM:'2', 'MD2') ; S0 = STATUS()
CRT 21:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('12', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('12', 'MD2') ; S0 = STATUS()
CRT 22:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('ab', 'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('ab', 'MCU') ; S0 = STATUS()
CRT 23:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'MCU':@VM:'MCT') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'MCU':@VM:'MCT') ; S0 = STATUS()
CRT 24:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(12345, 'MD2':@VM:'MR2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(12345, 'MD2':@VM:'MR2') ; S0 = STATUS()
CRT 25:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('12.34', 'MD2':@VM:'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('12.34', 'MD2':@VM:'MD2') ; S0 = STATUS()
CRT 26:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('abc', 'MCU':@VM:'MCL') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('abc', 'MCU':@VM:'MCL') ; S0 = STATUS()
CRT 27:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('1.5':@VM:'2.25', 'MD2':@VM:'MD1') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('1.5':@VM:'2.25', 'MD2':@VM:'MD1') ; S0 = STATUS()
CRT 28:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('150':@VM:'225', 'MD2':@VM:'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('150':@VM:'225', 'MD2':@VM:'MCU') ; S0 = STATUS()
CRT 29:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('a':@FM:'b', 'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('a':@FM:'b', 'MCU') ; S0 = STATUS()
CRT 30:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'MCU':@VM:'QWERTY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'MCU':@VM:'QWERTY') ; S0 = STATUS()
CRT 31:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'QWERTY':@VM:'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'QWERTY':@VM:'MCU') ; S0 = STATUS()
CRT 32:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', '':@VM:'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', '':@VM:'MCU') ; S0 = STATUS()
CRT 33:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', '') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', '') ; S0 = STATUS()
CRT 34:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(7, 'R1,9':@VM:'MCU') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(7, 'R1,9':@VM:'MCU') ; S0 = STATUS()
CRT 35:' [':X:'] ':S0:' ':S3
