R = 'first' : @FM : '1' : @VM : '2'
R<2,2> += 3
R<2,3,2>='last'
R<-1> = 'end'
CRT R<1>, R<2,2>, R<2,3,2>, R<3>
CRT '[' : R<20> : ']'
Index<1> = 2
CRT R<Index<1>,3,2>
