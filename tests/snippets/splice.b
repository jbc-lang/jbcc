A = 'A':@VM:'B':@SM:'C'
B = 'D':@SM:'E':@VM:'F'
CRT SPLICE(A,'-',B)
CRT SPLICE('1':@FM:'2','**','')
CRT SPLICE('','**','1':@VM:'2')
CRT SPLICE('a':@FM:'b',':','x':@VM:'y':@FM:'z':@FM:'w')
CRT SPLICE('a':@VM:@VM:'c','/', '1':@VM:'2':@VM:'3')
CRT SPLICE('a':@SM,'/', 'x':@SM)
CRT SPLICE(A,'',B)
CRT SPLICE('','+','')
CRT A
CRT B
