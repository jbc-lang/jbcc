* BITAND as in T24 R13 DM.GENERATE.ERWIN; 6 and 12 give 4 in the guide.
CRT BITAND(6, 12), BITAND('6.9', 12.9), BITAND(-1, 2147483648)
CRT BITAND(-1.9, 5), BITAND(4294967303, 7), BITAND(5, 1) AND BITAND(5, 2)
CRT '[':BITAND('', 'other'):']'
* BITNOT as in the same routine; the guide gives BITNOT(6) = 4294967289.
CRT BITNOT(6), BITNOT(-1), BITNOT(0), '[':BITNOT(''):']'
CRT BITAND(15, BITNOT(2 + 4))
