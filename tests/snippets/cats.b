L = 'p':@SM:'q':@VM:'r':@VM:'s'
R = '1':@VM:'2':@SM:'3'
CRT CATS(L,R) = ('p1':@SM:'q':@VM:'r2':@SM:'3':@VM:'s')
CRT CATS('',L) = L
CRT CATS(R,'') = R
CRT '[':CATS('',''):']'
CRT CATS(REUSE('ID-'),'A':@FM:'B') = ('ID-A':@FM:'ID-B')
CRT CATS('A':@VM:'B',REUSE('!')) = ('A!':@VM:'B!')
CRT CATS(@FM:'A':@FM,'B':@FM:@FM) = ('B':@FM:'A':@FM)
