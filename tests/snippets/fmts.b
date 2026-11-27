* The guide applies FMT independently to the elements.
Marks = @FM:@VM:@SM:@TM
A = '1.235':@VM:'':@SM:'-2.5':@FM:'100.25':@FM
CRT CONVERT(Marks, '^]~|', FMTS(A, 'R2*8'))
CRT '[':CONVERT(Marks, '^]~|', FMTS('abc':@FM:'d', '2L')):']'
CRT '[':FMTS('', 'R#5'):']'
