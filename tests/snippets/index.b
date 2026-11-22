Alphabet = 'abcdefghijklmnopqrstuvwxyzabc'
PRINT INDEX(Alphabet, 'a', 1), INDEX(Alphabet, 'a', 2), INDEX(Alphabet, 'jkl', 1)
PRINT INDEX(Alphabet, 'abc', 2), INDEX(Alphabet, 'abc', 3), INDEX(Alphabet, 'A', 1)
PRINT INDEX('aaaa', 'aa', 2), INDEX('aaa', 'aa', 2)
PRINT INDEX('', 'a', 1), INDEX('abc', '', 1), INDEX('abc', 'a', 0)
PRINT INDEX('a--a', 'a', '2.9'), INDEX('a', 'a', -1)
Record = 'ab' : @FM : 'c' : @FM : 'd'
IF INDEX(Record, @FM, 2) EQ 5 THEN PRINT 'field mark at byte 5'
PRINT INDEX(CHAR(195) : CHAR(169) : 'X', 'X', 1)
