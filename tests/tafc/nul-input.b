* tafc-emulation: prime
* NUL-BYTES.md: byte 0 in INPUT and KEYIN.
* tafc-stdin-hex: 6100620A000A630A0064
INPUT A
CRT 1:' ':OCONV(A, 'MX'):' ':LEN(A)
INPUT B
CRT 2:' ':OCONV(B, 'MX'):' ':LEN(B)
INPUT C
CRT 3:' ':C
K = KEYIN()
CRT 4:' ':OCONV(K, 'MX'):' ':LEN(K)
K = KEYIN()
CRT 5:' ':OCONV(K, 'MX'):' ':LEN(K)
