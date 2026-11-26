* This program prints its own source.
q = CHAR(39)
sep = CHAR(94)
d = '* This program prints its own source.^q = CHAR(39)^sep = CHAR(94)^d = ^FOR i = 1 TO DCOUNT(d, sep)^  text = FIELD(d, sep, i)^  IF i EQ 4 THEN text := q:d:q^  CRT text^NEXT i'
FOR i = 1 TO DCOUNT(d, sep)
  text = FIELD(d, sep, i)
  IF i EQ 4 THEN text := q:d:q
  CRT text
NEXT i
