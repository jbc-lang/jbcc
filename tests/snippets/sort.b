items = 'B' : @VM : 'AA' : @SM : 'A' : @TM : 'B'
CRT CHANGE(SORT(items), @AM, '|')
CRT items = ('B' : @VM : 'AA' : @SM : 'A' : @TM : 'B')
CRT CHANGE(SORT(@AM : '2' : @IM : '10' : CHAR(250) : CHAR(249)), @AM, '|')
CRT SORT('a' : CHAR(248) : 'b') = ('a' : CHAR(248) : 'b')
CRT '[' : SORT('') : ']'
CRT SORT(CHAR(200) : @VM : 'z') = ('z' : @AM : CHAR(200))
CRT SORT(@VM : @SM) = (@AM : @AM)
