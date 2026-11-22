REM Ignore the remainder of this line, even REM(1)
Month = REM(29, 12) ; REM ignore this too
CRT Month
IF REM(10, 4) THEN CRT 'nonzero'
CRT REM(-12.34, 0.5)
CRT REM('0004.50', 0)
CRT REM(17,
    REM this comment falls between arguments
    REM(9, 5))
PRECISION 2
CRT REM(3.456, 1)
