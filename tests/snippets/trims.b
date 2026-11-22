A = @FM:'  red   fox  ':@SM:'   ':@VM:'  blue ':@VM
CRT TRIMS(A) = (@FM:'red fox':@SM:@VM:'blue':@VM)
CRT A = (@FM:'  red   fox  ':@SM:'   ':@VM:'  blue ':@VM)
CRT '[':TRIMS(''):']'
CRT TRIMS(' x  y ') = 'x y'
CRT TRIMS(CHAR(9):'  x  ':CHAR(9)) = (CHAR(9):' x ':CHAR(9))
CRT FIELDS(TRIMS('  a   b':@VM:'  c d'),' ',1,1) = ('a':@VM:'c')
