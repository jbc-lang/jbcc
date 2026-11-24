DEFFUN BUMP(N)
A = 2:@VM:10:@SM:'b':@VM:'':@FM:'cat'
B = '02':@VM:3:@VM:'k':@VM:'':@VM:'last':@FM:'car'
CRT LES(A,B)
CRT LTS(A,B)
CRT GES(A,B)
CRT GTS(A,B)
CRT LES(2,10):LTS(2,2):GES('z','a'):GTS(2,2)
N = 1
CRT LES(REUSE(BUMP(N)),1:@VM:2:@VM:4)
CRT GTS(1:@VM:2:@VM:4,REUSE(N))
CRT N
CRT '[':GTS('',4):']'
