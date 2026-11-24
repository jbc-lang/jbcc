Values = @FM:'aaaaa':@VM:'Bb':@SM:'aa':@FM
CRT COUNTS(Values, 'aa')
CRT COUNTS(Values, '')
CRT COUNTS('', 'a'), COUNTS('', '')
CRT COUNTS('ab':@VM:'ab', 'b':@VM:'a'), COUNT('ab':@VM:'ab', 'b':@VM:'a')
CRT COUNTS(CHAR(195):CHAR(169):@TM:'x', '')
CRT SUM(COUNTS('aaa':@VM:'aa':@VM:'bbb', 'a'))
