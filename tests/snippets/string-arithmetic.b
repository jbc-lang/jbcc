* Guide SADD examples.
A = 4000000000000000000000000000000
B = 7
CRT SADD(A,B)
CRT SADD(4.33333333333333333,1.8)
* SADD and SSUB keep 14 fractional places, as the guide and TAFC
* PB201214 print. An optional third argument changes the limit.
A = 2.3000000123456789
B = 5.0000000000000001
CRT SSUB(A,B)
CRT SSUB(A,B,16)
CRT SADD(-5, 3):' ':SSUB(1, 1):' ':SSUB(-0.5, 0.25):' ':SADD('0.10', 0)
* SCMP orders decimal strings as -1, 0 or 1 (provisional).
CRT SCMP('100000000000000000001', '100000000000000000000'):' ':SCMP(1.50, 1.5):' ':SCMP(-2, 1)
