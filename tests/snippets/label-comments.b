GOTO 20
show.result:* A semicolon in a comment is ignored; STOP
PRINT 'called'
RETURN
20:  ! Start here; STOP
GOSUB show.result; resume: REM Continue on the next line; STOP
FOR REM = 2 TO 2
    Prefix = 'result='
    Text = Prefix:REM * 3
    PRINT Text, 'literal:*'
NEXT REM
