List = 'first':@FM:'second':@VM:'':@SM:'last'
D = 9
CRT D:':':REMOVE(List,D):':':D
REMOVE Part FROM List SETTING D
CRT Part,D
CRT '[':REMOVE(List,D):']',D
CRT REMOVE(List,D),D
CRT '[':REMOVE(List,D):']',D
REMOVE Part FROM List SETTING D
CRT Part,D
List = List
CRT REMOVE(List,D),D
Copy = List
CRT REMOVE(Copy,D),D
CRT REMOVE(List,D),D
DIM M(1), Codes(1)
M(1) = 'one':@TM:'two'
CRT REMOVE(M(1),Codes(1)),Codes(1)
REMOVE Part FROM M(1) SETTING D
CRT Part,D
CRT REMOVE(M(1):'tail',D),D
CRT REMOVE('left':@VM:'right',D),D
List = 'a':@FM:'b'
LOOP Part = REMOVE(List,D) UNTIL NOT(Part:D)
  CRT Part,D
REPEAT
