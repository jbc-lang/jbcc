L = 'a':@VM:'02':@SM:'extra':@VM:'c'
R = 'b':@VM:2:@VM:'c'
CRT EQS(L,R) = ('0':@VM:'1':@SM:'0':@VM:'1')
CRT EQS(R,L) = EQS(L,R)
CRT EQS('a':@FM:@FM:'z', 'a':@FM:'b') = ('1':@FM:@FM:'0')
CRT EQS('a':@VM, 'a') = ('1':@VM:'0')
CRT EQS('':@VM:'a','') = (@VM:'0')
CRT EQS(REUSE('2'), 2:@VM:3:@FM:'02') = ('1':@VM:'0':@FM:'1')
CRT EQS(R,REUSE('c')) = ('0':@VM:'0':@VM:'1')
CRT '[':EQS('','x'):']'
CRT EQS('1.0','1')
CRT EQS(REUSE(''), 'x':@VM:'y') = @VM
PRECISION 2
CRT EQS('1.234':@VM:'1.3', '1.231':@VM:'1.2') = ('1':@VM:'0')
