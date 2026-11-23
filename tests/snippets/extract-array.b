* Field, value and negative-field selection follow the guide.
R = 'first':@FM:'one':@VM:'two':@SM:'detail':@FM:'last'
IF EXTRACT(R, 2) = R<2> THEN CRT 'field'
IF EXTRACT(R, 2, 2) = R<2,2> THEN CRT 'value'
CRT EXTRACT(R, 2, 2, 2)
IF EXTRACT(R, 2, 0, 0) = R<2> THEN CRT 'trailing zeros'
IF EXTRACT(R, 2, 2, 0) = R<2,2> THEN CRT 'trailing zero'
CRT EXTRACT(R<2>, 1, 1)
CRT EXTRACT(R, 2.9, '02.8', 2)
CRT '[':EXTRACT(R, -1):'][':EXTRACT(R, 9):'][':EXTRACT(R, 2, 9):']'
CRT '[':EXTRACT(R, 2, 0, 1):'][':EXTRACT(R, '99999999999999999999999'):']'
