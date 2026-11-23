* The ITYPE and SSELECT examples assign the record context explicitly.
CRT '[':@ID:']'
ID = 'local'
@ID = 'seed-':(1+2)
CRT ID:':':@ID[6,1]
SELECT 'ordinary'
READNEXT Key THEN CRT Key:':':@ID ELSE STOP
SELECT 'one':@FM:'two' TO Keys
READNEXT @ID, Position FROM Keys SETTING Status THEN CRT @ID:':':Position:':':Status ELSE STOP
LOOP WHILE READNEXT @ID FROM Keys DO
    CRT @ID
REPEAT
CRT '[':@ID:']'
