* tafc-emulation: prime
* TAFC-CROSSCHECK.md: OCONV L and R codes are length and range tests.
* Each case runs from STATUS() 0 and from STATUS() 3.
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('ab', 'L0') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('ab', 'L0') ; S0 = STATUS()
CRT 1:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('ab', 'L2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('ab', 'L2') ; S0 = STATUS()
CRT 2:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L2') ; S0 = STATUS()
CRT 3:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L1,3') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L1,3') ; S0 = STATUS()
CRT 4:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abcd', 'L1,3') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abcd', 'L1,3') ; S0 = STATUS()
CRT 5:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L3,3') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L3,3') ; S0 = STATUS()
CRT 6:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L5,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L5,9') ; S0 = STATUS()
CRT 7:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('ab', 'L3') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('ab', 'L3') ; S0 = STATUS()
CRT 8:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('ab', 'L0,2') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('ab', 'L0,2') ; S0 = STATUS()
CRT 9:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'L0') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'L0') ; S0 = STATUS()
CRT 10:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'L') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'L') ; S0 = STATUS()
CRT 11:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L2,') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L2,') ; S0 = STATUS()
CRT 12:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'LX') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'LX') ; S0 = STATUS()
CRT 13:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('ab', 'L#6') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('ab', 'L#6') ; S0 = STATUS()
CRT 14:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('a':@VM:'bc', 'L') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('a':@VM:'bc', 'L') ; S0 = STATUS()
CRT 15:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'L3,1') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'L3,1') ; S0 = STATUS()
CRT 16:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(12, 'L2X') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(12, 'L2X') ; S0 = STATUS()
CRT 17:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(5, 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(5, 'R1,9') ; S0 = STATUS()
CRT 18:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(15, 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(15, 'R1,9') ; S0 = STATUS()
CRT 19:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(15, 'R1,9;20,30') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(15, 'R1,9;20,30') ; S0 = STATUS()
CRT 20:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(25, 'R1,9;20,30') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(25, 'R1,9;20,30') ; S0 = STATUS()
CRT 21:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(9, 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(9, 'R1,9') ; S0 = STATUS()
CRT 22:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(1, 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(1, 'R1,9') ; S0 = STATUS()
CRT 23:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(0.5, 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(0.5, 'R1,9') ; S0 = STATUS()
CRT 24:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('abc', 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('abc', 'R1,9') ; S0 = STATUS()
CRT 25:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV('', 'R1,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV('', 'R1,9') ; S0 = STATUS()
CRT 26:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(-3, 'R-5,0') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(-3, 'R-5,0') ; S0 = STATUS()
CRT 27:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(5, 'R9,1') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(5, 'R9,1') ; S0 = STATUS()
CRT 28:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(5, 'R5') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(5, 'R5') ; S0 = STATUS()
CRT 29:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(1234.5, 'R2,$#15') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(1234.5, 'R2,$#15') ; S0 = STATUS()
CRT 30:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(12, 'R#6') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(12, 'R#6') ; S0 = STATUS()
CRT 31:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(12, 'R') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(12, 'R') ; S0 = STATUS()
CRT 32:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(5, 'R1.5,9') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(5, 'R1.5,9') ; S0 = STATUS()
CRT 33:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(5, 'R1,9;') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(5, 'R1,9;') ; S0 = STATUS()
CRT 34:' [':X:'] ':S0:' ':S3
X = ICONV('31 FEB 2020', 'D') ; X = OCONV(12, '6R') ; S3 = STATUS()
X = ICONV('1/1/2020', 'D') ; X = OCONV(12, '6R') ; S0 = STATUS()
CRT 35:' [':X:'] ':S0:' ':S3
