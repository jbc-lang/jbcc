Text = 'ABCDEFCDYZ'
CHANGE 'C' TO 'Q' IN Text
PRINT Text
CHANGE 'QD' TO 'nnn' IN Text
PRINT Text, CHANGE(Text,'YZ','+-')
DIM Row(2)
Row(2) = 'pre' : @FM : Text
CHANGE 'nnn' WITH '' IN Row(2)<2>
PRINT Row(2)<1>, Row(2)<2>, Text
PRINT CHANGE('aaaaa','aa','X'), CHANGE('aaa','a','aa'), CHANGE('abc','','X')
PRINT CHANGE('axaxax','x','!',2), CHANGE('axaxax','x','!',1,2)
PRINT CHANGE('axaxax','x','',0,2), CHANGE('axaxax','x','!',1,7)
N = 12345.67
CHANGE 3 TO 9 IN N
PRINT N
CHANGE @FM TO ' / ' IN Row(2)
PRINT Row(2)
CHANGE = 'abc'
PRINT CHANGE(CHANGE,'b','B')
