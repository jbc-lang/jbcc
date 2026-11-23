CRT '[':42"4R":']'
CRT 'short'"L#7":'.'
Mask = 'R%4'
Masks = 'R%2':@FM:Mask
DIM Matrix(1)
Matrix(1) = 'L#3'
CRT 7 Mask, 3 Masks<1>, 'x' Matrix(1):'.'
CRT 'sum=':2 + 3 "R%3"
CRT 'x':('y' "L#4"):'z'
CRT '[':('x':'y') "6R":']'
CRT 1 + 2 "R%3" * 2
CRT IF 1 THEN 2 "R%3" ELSE 3
CRT IF 0 THEN 2 ELSE (3 "R%3")
THEN= 'R%9'
ELSE= 'R%9'
IF 1 THEN CRT 4 ELSE CRT 5
FROM = 'R%9'
TO = 'R%9'
BY = 'R%9'
ON = 'R%9'
SETTING = 'R%9'
LOCATE 'x' IN 'x' BY 'AL' SETTING P THEN CRT P
FOR I = 1 TO 2
  CRT I
NEXT I
