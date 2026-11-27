A = 1 : @FM : 2 : @FM : 3.1
PRINT SUM(A)
A<4> = 6
PRINT SUM(A)
A<4,2> = 7
PRINT CONVERT(@FM, '^', SUM(A))
A<4,3> = 'text'
PRINT CONVERT(@FM, '^', SUM(A))
A<4,3,2> = 8
PRINT CONVERT(@FM : @VM, '^]', SUM(A))
PRINT SUM(-2), SUM(''), SUM('abc')
A = @FM : -4 : @VM : 1 : @FM
PRINT CONVERT(@FM, '^', SUM(A))
PRINT SUM(SUM(A))
