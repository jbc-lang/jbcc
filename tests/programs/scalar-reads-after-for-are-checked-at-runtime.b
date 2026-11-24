GET(ARG.) Bound
FOR I = 1 TO Bound WHILE Bound # 4
    IF Bound = 3 THEN CONTINUE
    IF Bound = 5 THEN EXIT
    Value = I
UNTIL I = 2
NEXT I
IF Bound # -1 THEN CRT Value
