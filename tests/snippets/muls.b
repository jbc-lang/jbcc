* Mark alignment, zero padding and empty pairs follow the guide.
A = 3:@VM:5:@VM:7:@SM:11
B = 2:@VM:4:@VM:6:@VM:8:@FM:10
Marks = @FM:@VM:@SM
Visible = '^]':CHAR(92)
CRT CONVERT(MULS(A, B), Marks, Visible)
CRT CONVERT(MULS('':@VM:2:@VM:3, 4:@VM:@VM:8:@VM), Marks, Visible)
CRT CONVERT(MULS('', 3:@VM:5), Marks, Visible)
CRT CONVERT(MULS(REUSE(-2), 3:@FM:5:@VM:7), Marks, Visible)
CRT CONVERT(MULS(A, REUSE(0)), Marks, Visible)
CRT CONVERT(MULS(99999999:@VM:99999999, REUSE(99999999)), Marks, Visible)
PRECISION 2
CRT CONVERT(MULS(1.129:@VM:0.085, REUSE(2.5)), Marks, Visible)
