* The guide uses zero for empty and missing positions.
A = 1:@VM:@VM:6:@SM:19:@FM:9
B = 2:@VM:5:@VM:3:@VM:8:@FM:4:@FM:12
Marks = @FM:@VM:@SM
Visible = '^]':CHAR(92)
CRT CONVERT(Marks, Visible, SUBS(A, B))
CRT SUBS('', '')
CRT CONVERT(Marks, Visible, SUBS('', 1:@VM:2))
CRT CONVERT(Marks, Visible, SUBS(REUSE(11), 4:@FM:8:@VM:''))
CRT CONVERT(Marks, Visible, SUBS(4:@FM:8:@VM:'', REUSE(11)))
PRECISION 2
CRT CONVERT(Marks, Visible, SUBS(2.809:@VM:0.125, REUSE(0.539)))
