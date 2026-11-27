* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 5: masked decimal conversions (MD, MR, ML).
V = 1234567 : @FM : -1234567 : @FM : 5 : @FM : 0 : @FM : '' : @FM : 12.345 : @FM : -0.4 : @FM : 'abc' : @FM : 99999999999999999999
M = 'MD0!MD2!MD2,!MD2Z!MD0T!MD6!MD9!MD2$!MD2-!MD2C!MD2D!MD24!MD2,$!MR2!ML2!MD2Z,!MD3P!MD1E!MD2M!MD2,C'
FOR J = 1 TO DCOUNT(M, '!')
   MASK = FIELD(M, '!', J)
   IF MASK = '' THEN CONTINUE
   LINE = MASK:':'
   FOR I = 1 TO DCOUNT(V, @FM)
      LINE := ' [':OCONV(V<I>, MASK):']'
   NEXT I
   CRT LINE
NEXT J
CRT 'iconv [':ICONV('12.345', 'MD2'):'] [':ICONV('-1,234.5', 'MD2'):'] [':ICONV('12', 'MD2'):'] [':ICONV('abc', 'MD2'):']':STATUS():' [':ICONV('$1,234.56', 'MD2'):'] [':ICONV('12.345', 'MD0'):'] [':ICONV('1.5', 'MD24'):']'
CRT 'fmt [':FMT(1234567, 'MD2'):'] [':FMT(1234567, 'MD2,'):']'
