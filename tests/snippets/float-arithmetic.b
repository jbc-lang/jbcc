* Guide FADD example: PRECISION 7 gives 24.2334002.
PRECISION 7
CRT FADD(0.5044, 23.7290002)
* Guide FDIV and FMUL examples are not subject to PRECISION.
PRECISION 4
CRT FDIV(1, 7)
CRT FMUL(2.54, 5.703358)
CRT FDIV(10, 4):' ':FMUL(-3, 4):' ':FDIV(1, 3)
* FCMP orders floating-point values as -1, 0 or 1 (provisional).
CRT FCMP(1.5, 2):' ':FCMP(2, 2.0):' ':FCMP(3, -2)
