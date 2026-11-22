FOR I = 1 TO 3
    ON I GOSUB first, 20,
        first
    CRT 'back'
NEXT I
ON 1+1 GOTO wrong, finish:
wrong: CRT 'wrong'
STOP
first: CRT 'first'
RETURN
20: CRT 'second'
RETURN
finish: ON 1 GOSUB redirect
CRT 'wrong'
STOP
redirect: RETURN TO done
done: CRT 'done'
