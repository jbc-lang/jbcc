L = 'A':@SM:'B':@VM:'02':@FM:'x':@VM:''
R = 'A':@VM:2:@FM:'y':@VM:9
expected = '0':@SM:'1':@VM:'0':@FM:'1':@VM:''
CRT NES(L,R) = expected
CRT NES(R,L) = expected
CRT NES('a':@VM, 'a') = ('0':@VM:'1')
CRT NES(REUSE('B'), 'A':@FM:'B') = ('1':@FM:'0')
CRT NES('2':@VM:'02', REUSE(2)) = ('0':@VM:'0')
CRT '[':NES('',1):']'
CRT NES('10','2')
