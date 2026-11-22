Name = 'CUSTOMERS'
OPEN Name TO DataFile ELSE STOP
WRITE 'data' ON DataFile, 'id'
OPEN '', Name TO SameFile ELSE STOP
READ R FROM SameFile, 'id' THEN CRT R
Section = 'DI' : 'CT'
OPEN Section, Name TO Dictionary ELSE STOP
WRITE 'definition' ON Dictionary, 'id'
READ R FROM Dictionary, 'id' THEN CRT R
OPEN 'DICT', Name ELSE STOP
DELETE 'id'
READ R FROM Dictionary, 'id' ELSE CRT 'removed from dictionary'
READ R FROM DataFile, 'id' THEN CRT R
OPEN 'DICT', 'DATA.ONLY' TO Dictionary ELSE CRT 'missing dictionary'
WRITE 'no' ON Dictionary, 'id' ELSE CRT 'descriptor cleared'
OPEN '', 'DICT.ONLY' TO DataFile ELSE CRT 'missing data file'
