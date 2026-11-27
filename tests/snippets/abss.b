* The guide applies ABS independently and preserves empty elements.
Marks = @FM:@VM:@SM
A = '-200':@VM:100:@VM:'':@SM:-11:@FM:0:@FM
CRT CONVERT(Marks, '^]~', ABSS(A))
CRT '[':ABSS(''):']'
CRT ABSS('-9223372036854775808')
PRECISION 2
CRT CONVERT(Marks, '^]~', ABSS('-.009':@SM:'-1.239':@VM:'3.146'))
