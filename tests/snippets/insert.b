B = 'Field 1':@VM:2:@VM:3:@VM:5:@FM:'Field 2'
A = INSERT(B, 1, 4; 'Field1Value4')
CRT A
CRT B
CRT INSERT(B, 1, 4, 0, 'Field1Value4')
CRT INSERT('tail', 1; 'head')<1>; CRT B<INSERT('', 1; 2)>
CRT INSERT('two', 1, 1, 1; INSERT('one', 1; 'zero'))
CRT INSERT('', 2, 2, 2, 'x')
