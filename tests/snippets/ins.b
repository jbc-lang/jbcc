Marks = @FM : @VM : @SM
Values = ''
FOR I = 1 TO 4
    INS I BEFORE Values<-1>
NEXT I
INS 'X' BEFORE Values<2>
INS 'v' BEFORE Values<3,2>
INS 's' BEFORE Values<3,2,1>
PRINT CONVERT(Values, Marks, '|:;')
DIM Rows(2)
Rows(1) = Values
INS 'far' BEFORE Rows(2)<3,2,3>
PRINT CONVERT(Rows(2), Marks, '|:;')
INS 'new' BEFORE Rows(2)<-7,-2,-9>
PRINT CONVERT(Rows(2), Marks, '|:;')
PRINT CONVERT(Rows(1), Marks, '|:;')
R = 'a' : @FM : '' : @FM : 'b'
INS '' BEFORE R<1>
INS R<2> BEFORE R<3>
PRINT CONVERT(R, Marks, '|:;')
INS 'last' BEFORE R<5,-1>
INS 'first' BEFORE R<5,1.9,0>
PRINT CONVERT(R, Marks, '|:;')
