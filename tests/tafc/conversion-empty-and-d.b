* tafc-emulation: prime
* TAFC-CROSSCHECK.md: empty values, MT STATUS and D codes in chains.
* Each case runs from STATUS() 0 and from STATUS() 3.
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'MTS') ; S0 = STATUS()
CRT 1:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'MT') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'MT') ; S0 = STATUS()
CRT 2:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'D') ; S0 = STATUS()
CRT 3:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'MD2') ; S0 = STATUS()
CRT 4:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'MR2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'MR2') ; S0 = STATUS()
CRT 5:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('':@VM:'1', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('':@VM:'1', 'MD2') ; S0 = STATUS()
CRT 6:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('':@VM:'1', 'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('':@VM:'1', 'MTS') ; S0 = STATUS()
CRT 7:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('':@VM:'1', 'MR2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('':@VM:'1', 'MR2') ; S0 = STATUS()
CRT 8:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('25:00', 'MT') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('25:00', 'MT') ; S0 = STATUS()
CRT 9:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('25:00', 'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('25:00', 'MTS') ; S0 = STATUS()
CRT 10:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('24:00', 'MT') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('24:00', 'MT') ; S0 = STATUS()
CRT 11:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('', 'MT') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('', 'MT') ; S0 = STATUS()
CRT 12:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('', 'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('', 'MD2') ; S0 = STATUS()
CRT 13:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('19671231', 'D':@VM:'D4') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('19671231', 'D':@VM:'D4') ; S0 = STATUS()
CRT 14:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('19671231', 'D4':@VM:'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('19671231', 'D4':@VM:'MD2') ; S0 = STATUS()
CRT 15:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONV('19671231', 'D/':@VM:'MD2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONV('19671231', 'D/':@VM:'MD2') ; S0 = STATUS()
CRT 16:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(0, 'D':@VM:'') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(0, 'D':@VM:'') ; S0 = STATUS()
CRT 17:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(0, 'D4':@VM:'') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(0, 'D4':@VM:'') ; S0 = STATUS()
CRT 18:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(0, 'D/':@VM:'MCL') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(0, 'D/':@VM:'MCL') ; S0 = STATUS()
CRT 19:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(0, 'DD':@VM:'MTS') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(0, 'DD':@VM:'MTS') ; S0 = STATUS()
CRT 20:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('1', 'D':@VM:'DUMMY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('1', 'D':@VM:'DUMMY') ; S0 = STATUS()
CRT 21:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('1', 'D':@VM:'DUMMY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('1', 'D':@VM:'DUMMY') ; S0 = STATUS()
CRT 22:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('1', 'MCU':@VM:'DUMMY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('1', 'MCU':@VM:'DUMMY') ; S0 = STATUS()
CRT 23:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONVS('a':@VM:'b', 'MCU':@VM:'DUMMY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONVS('a':@VM:'b', 'MCU':@VM:'DUMMY') ; S0 = STATUS()
CRT 24:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = ICONVS('a':@VM:'1/2/2020', 'MCU':@VM:'DUMMY') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = ICONVS('a':@VM:'1/2/2020', 'MCU':@VM:'DUMMY') ; S0 = STATUS()
CRT 25:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('a', 'MCU':@VM:'D') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('a', 'MCU':@VM:'D') ; S0 = STATUS()
CRT 26:' [':X:'] ':S0:' ':S3
