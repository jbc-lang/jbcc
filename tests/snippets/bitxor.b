* Expected output: observed TAFC PB201214 run (unsigned 32-bit results;
* empty and nonnumeric operands count as 0).
CRT BITXOR(6, 12)
CRT BITXOR('6.9', 12.9)
CRT BITXOR(-1.9, 5)
CRT BITXOR(2147483647, -1)
CRT BITXOR(2147483648, 1)
CRT BITXOR(4294967296, 7)
CRT BITXOR('18446744073709551617', 3)
CRT BITXOR(-4294967297, 0)
CRT '[':BITXOR('', 5):'] [':BITXOR('other', ''):']'
