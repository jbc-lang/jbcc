DIM Rows(2)
Marks = @FM : @VM : @SM
Rows(1) = 'left' : @FM : 'A' : @VM : 'x' : @SM : 'y' : @SM : 'z' : @VM : 'B' : @FM : 'right'
Rows(2) = Rows(1)
DEL Rows(1)<2,2,2.9>
PRINT CONVERT(Marks, '|:;', Rows(1))
DEL Rows(1)<2,1>
DEL Rows(1)<2,2>
DEL Rows(1)<2,1,2>
DEL Rows(1)<2,1,1>
PRINT CONVERT(Marks, '|:;', Rows(1))
DEL Rows(1)<2>
PRINT CONVERT(Marks, '|:;', Rows(1)), Rows(2)<2,2,2>
R = @FM : 'mid' : @FM
DEL R<4>
DEL R<-1>
DEL R<0>
DEL R<2,8>
DEL R<999999999999999999999999>
PRINT CONVERT(@FM, '|', R)
DEL R<1>
PRINT CONVERT(@FM, '|', R)
DEL R<2>
PRINT R
DEL R<1>
PRINT LEN(R)
