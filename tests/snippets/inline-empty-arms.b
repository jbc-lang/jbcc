Total = 0
FOR I = 1 TO 2
    IF I = 1 THEN END
    Total += 1
NEXT I
CRT Total
IF 0 THEN END ELSE CRT 'else'
IF 1 THEN CRT 'then' ELSE END
IF 0 ELSE END; CRT 'after'
OPEN 'missing' THEN END ELSE CRT 'open miss'
END
