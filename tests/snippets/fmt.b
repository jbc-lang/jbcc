N = 1234.56
PRINT '[' : FMT(N,'R2#10') : ']', FMT(N,'L2%10'), FMT(N,'R2*10')
PRINT FMT(9.995,'R2'), FMT(-9.995,'L2'), FMT(-0.004,'R2'), FMT('999999999999999999999.9','R0')
PRINT FMT(12,'R6'), FMT(12,'R%4'), FMT('7',"3'0'R")
Mask = '4' : '"0"' : 'R'
PRINT FMT(8,Mask), '[' : FMT('ab','5L') : ']'
PRINT CONVERT(FMT('ABCDEFGHIJ','4L'),CHAR(251),'|') : ']'
PRINT CONVERT(FMT('ABCDE','3R'),CHAR(251),'|') : ']'
PRINT FMT('abcdef','R#4'), FMT('abcdef','L#4'), LEN(FMT('','3L'))
