* The guide's left and right orders differ for these unequal lengths.
CRT COMPARE('XY999', 'XY1000')
CRT COMPARE('XY999', 'XY1000', 'R')
CRT COMPARE('a', 'ab', 'L')
CRT COMPARE('abc', 'abc')
CRT COMPARE('2', '02')
CRT COMPARE('x', ' x', 'R')
CRT COMPARE('', '')
CRT COMPARE(CHAR(255), CHAR(1))
