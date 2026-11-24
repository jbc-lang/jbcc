CRT LENDP(''), LENDP('abc '), LENDP(-12.5)
Controls = CHAR(9):CHAR(10):CHAR(127)
Marks = @FM:@VM:@SM:@TM
Text = 'é漢'
CRT LENDP(Controls), LEN(Controls), BYTELEN(Controls)
CRT LENDP(Marks), LEN(Marks), BYTELEN(Marks)
CRT LENDP(Text), LEN(Text), BYTELEN(Text)
IF LENDP(Text[1,2]) > 0 THEN CRT 'present' ELSE ABORT
