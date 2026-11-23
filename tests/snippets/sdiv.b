* The first two quotients come from the SDIV guide.
CRT SDIV(2, 3)
CRT SDIV(355, 113)
* Truncation and the optional precision follow provisional jbcc rules.
CRT SDIV(2, 3, 4)
CRT SDIV(2, 3, -1)
CRT SDIV('-2', 3, 4)
CRT SDIV('-1', 100, 1)
CRT SDIV('999999999999999999990000', '-0.0001')
CRT SDIV('0.00012', '0.03')
CRT SDIV('0.0012', '0.000004')
CRT SDIV(10, 8, 1000000000)
CRT SDIV(2, 17, 40)
CRT SDIV(5, 2, 0)
CRT SDIV(0, 2)
PRECISION 1
CRT SMUL(SDIV(1, 8, 3), 100)
CRT SDIV(2, 3)
