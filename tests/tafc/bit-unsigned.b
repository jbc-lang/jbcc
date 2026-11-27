* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: bit functions return unsigned 32-bit values.
CRT BITOR(-1, 0), BITAND(-1, -1), BITXOR(-1, 0), BITAND(-1, 255)
CRT BITOR(2147483647, 1), BITNOT(0), BITNOT(5), BITNOT(-1), BITNOT(-5)
CRT BITXOR(1, 3), BITAND(-2, 3), BITOR(4294967296, 1)
