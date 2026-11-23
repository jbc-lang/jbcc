* The guide preserves an unmatched dividend and zero-fills an unmatched divisor position.
A = 9:@VM:8:@VM:10:@SM:'7.0010'
B = 3:@VM:2:@VM:4:@VM:5:@FM:6
Marks = @FM:@VM:@SM
Visible = '^]':CHAR(92)
CRT CONVERT(DIVS(A, B), Marks, Visible)
CRT CONVERT(DIVS('':@VM:4:@VM:5, 2:@VM:@VM:2), Marks, Visible)
CRT CONVERT(DIVS(2:@VM:7, ''), Marks, Visible)
CRT CONVERT(DIVS(REUSE(10), 4:@FM:5), Marks, Visible)
PRECISION 2
CRT CONVERT(DIVS(2:@VM:7, REUSE(3)), Marks, Visible)
