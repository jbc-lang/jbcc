* The guide describes mark alignment, unmatched values and null pairs.
A = 1:@VM:2:@SM:3:@FM:4
B = 5:@VM:6:@VM:7:@FM:8:@FM:9
Marks = @FM:@VM:@SM
Visible = '^]':CHAR(92)
CRT CONVERT(Marks, Visible, ADDS(A, B))
CRT CONVERT(Marks, Visible, ADDS(2:@VM:@VM:4:@VM, 3:@VM:5:@VM:@VM:9:@VM:''))
CRT CONVERT(Marks, Visible, ADDS('', 1:@VM:2))
CRT CONVERT(Marks, Visible, ADDS(REUSE(7), A))
CRT CONVERT(Marks, Visible, ADDS(A, REUSE(999)))
CRT CONVERT(Marks, Visible, ADDS(A, REUSE('')))
CRT ADDS(REUSE(7), REUSE(8))
PRECISION 2
CRT CONVERT(Marks, Visible, ADDS('1.126':@VM:'20.009', REUSE('0.066')))
