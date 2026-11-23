R<1,2,1> = "result"
K<1> = 2
OUT = R <1,K <1>,1>
CRT OUT
CRT LEN(R <1,2,1>), R <1,2,1>[2,3]
IF R <1,2,1> = "result" AND K <1> > 1 THEN CRT "ok"
CRT R<1,K <1>,1>
CRT 2 < 3 > 0, 2 < 3 >= 0, 2 < 3 AND 4 > 1
LOCATE R <1,2,1> IN R <1> SETTING POS THEN CRT POS
CRT K <1> + 3
CRT R <1,2>
