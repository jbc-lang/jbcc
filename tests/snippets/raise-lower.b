Bytes = ''
FOR I = 247 TO 255
    Bytes := CHAR(I)
NEXT I
Text = 'A' : Bytes : 'z'
Digits = '012345678'
PRINT CONVERT(RAISE(Text), Bytes, Digits)
PRINT CONVERT(LOWER(Text), Bytes, Digits)
PRINT CONVERT(Text, Bytes, Digits)
Record = 'one' : @FM : 'two'
Nested = LOWER(Record)
PRINT Nested<1,2>, RAISE(Nested) = Record
PRINT LEN(RAISE('')), LEN(LOWER(''))
