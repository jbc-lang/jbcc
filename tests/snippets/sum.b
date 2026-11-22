A = 1 : @FM : 2 : @FM : 3.1
PRINT SUM(A)
A<4> = 6
PRINT SUM(A)
A<4,2> = 7
PRINT CONVERT(SUM(A), @FM, '^')
A<4,3> = 'text'
PRINT CONVERT(SUM(A), @FM, '^')
A<4,3,2> = 8
PRINT CONVERT(SUM(A), @FM : @VM, '^]')
PRINT SUM(-2), SUM(''), SUM('abc')
A = @FM : -4 : @VM : 1 : @FM
PRINT CONVERT(SUM(A), @FM, '^')
PRINT SUM(SUM(A))
