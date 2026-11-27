* Expected output: observed TAFC PB201214 run (unsigned 32-bit results;
* empty and nonnumeric operands count as 0).
CRT BITOR('6.9', 12.9), BITOR(2147483648, 1)
CRT BITOR(-1.9, 5), BITOR(4294967296, 7), BITOR(6, XTD(40000000))
CRT '[':BITOR('', 'other'):']'
