CRT MATCHFIELD('QA123end', '2A0N3A', 2)
CRT MATCHFIELD('box A 00742', '0X5N', 2)
CRT '[' : MATCHFIELD('QA123z', '2A3N', 1) : ']'
Pattern = '3N' : @VM : "0A'/'2N"
CRT MATCHFIELD('ABC/10', Pattern, 2)
CRT '[' : MATCHFIELD('123', Pattern, 2) : ']'
CRT '[' : MATCHFIELD('123', '0A3N', 1) : ']'
CRT MATCHFIELD('abc', '0X0X', 1)
CRT '[' : MATCHFIELD('abc', '0X0X', 2) : ']'
CRT '[' : MATCHFIELD('', '0X', 1) : ']'
CRT '[' : MATCHFIELD('x', '', 1) : ']'
CRT MATCHFIELD('AB12', '2A2N' : @VM : '4X', 1)
