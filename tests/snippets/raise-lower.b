Bytes = ''
FOR I = 247 TO 255
    Bytes := CHAR(I)
NEXT I
Text = 'A' : Bytes : 'z'
Digits = '012345678'
PRINT CONVERT(Bytes, Digits, RAISE(Text))
PRINT CONVERT(Bytes, Digits, LOWER(Text))
PRINT CONVERT(Bytes, Digits, Text)
Record = 'one' : @FM : 'two'
Nested = LOWER(Record)
PRINT Nested<1,2>, RAISE(Nested) = Record
PRINT LEN(RAISE('')), LEN(LOWER(''))
