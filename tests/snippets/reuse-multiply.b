* A direct scalar REUSE operand broadcasts using the MULS rules.
A = 2:@VM:3:@SVM:4:@FM:'':@VM:5
CRT A * REUSE(12 / 4)
CRT REUSE(3) * A
CRT REUSE(2) * REUSE(4) * 3
CRT 2 + REUSE(3) * 4
CRT '[':(2:@VM:3) * REUSE(2 ^ 3):']'
