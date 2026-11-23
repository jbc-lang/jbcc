* The guide uses zero for empty and missing positions.
A = 1:@VM:@VM:6:@SM:19:@FM:9
B = 2:@VM:5:@VM:3:@VM:8:@FM:4:@FM:12
Marks = @FM:@VM:@SM
Visible = '^]':CHAR(92)
CRT CONVERT(SUBS(A, B), Marks, Visible)
CRT SUBS('', '')
CRT CONVERT(SUBS('', 1:@VM:2), Marks, Visible)
CRT CONVERT(SUBS(REUSE(11), 4:@FM:8:@VM:''), Marks, Visible)
CRT CONVERT(SUBS(4:@FM:8:@VM:'', REUSE(11)), Marks, Visible)
PRECISION 2
CRT CONVERT(SUBS(2.809:@VM:0.125, REUSE(0.539)), Marks, Visible)
