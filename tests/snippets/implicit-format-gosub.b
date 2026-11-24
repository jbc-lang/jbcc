GOSUB INIT.MASK
IF 'Y ' = 'Y' Mask THEN CRT 'matched' ELSE ABORT
CRT '[':'Y' Mask:']'
STOP
INIT.MASK:
Mask = '2L'
RETURN
