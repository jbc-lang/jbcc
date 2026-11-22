IF 0 THEN CRT 'wrong'
* an intervening comment

   ELSE CRT 'inline'

IF 0 THEN
   CRT 'wrong'
END
! alternate block
ELSE
   CRT 'block'
END

FOR N = 0 TO 2
    IF N THEN IF N EQ 2 THEN CRT 'inner true'
        ELSE CRT 'inner false'
    ELSE CRT 'outer false'
NEXT N

OPEN 'missing'
    THEN CRT 'wrong'
    ELSE CRT 'open failed'
IF 0 THEN CRT 'wrong'
ELSE.VALUE = 'separate statement'
CRT ELSE.VALUE
