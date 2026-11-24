EQUATE RetryLabel TO 020
GOSUB 10
GOSUB 020
GOSUB 20
CRT 'continued',
    7,
    8
STOP
10 * label followed by a comment
    CRT 'bare'
    RETURN
RetryLabel
    CRT 'equated'
    RETURN
20 CRT 'inline'
    RETURN
