* tafc-emulation: prime
* TAFC-CROSSCHECK.md: MATPARSE trailing delimiters, USING '' and ranges.
DIM M1(4)
MAT M1 = 'z'
MATPARSE M1 FROM '':@FM:'b' SETTING N
CRT 1:' ':N
CRT M1(0):'|':M1(1):'|':M1(2):'|':M1(3):'|':M1(4)
DIM M2(4)
MAT M2 = 'z'
MATPARSE M2 FROM 'a':@FM:'':@FM:'b' SETTING N
CRT 2:' ':N
CRT M2(0):'|':M2(1):'|':M2(2):'|':M2(3):'|':M2(4)
DIM M3(4)
MAT M3 = 'z'
MATPARSE M3 FROM 'a':@FM:@FM SETTING N
CRT 3:' ':N
CRT M3(0):'|':M3(1):'|':M3(2):'|':M3(3):'|':M3(4)
DIM M4(4)
MAT M4 = 'z'
MATPARSE M4 FROM @FM SETTING N
CRT 4:' ':N
CRT M4(0):'|':M4(1):'|':M4(2):'|':M4(3):'|':M4(4)
DIM M5(4)
MAT M5 = 'z'
MATPARSE M5 FROM 'a':@FM:'b':@FM:'c':@FM:'' SETTING N
CRT 5:' ':N
CRT M5(0):'|':M5(1):'|':M5(2):'|':M5(3):'|':M5(4)
DIM M6(4)
MAT M6 = 'z'
MATPARSE M6 FROM 'a':@FM:'b':@FM:'c':@FM:'':@FM:'' SETTING N
CRT 6:' ':N:' [':M6(4):']'
CRT M6(0):'|':M6(1):'|':M6(2):'|':M6(3):'|':M6(4)
DIM M7(4)
MAT M7 = 'z'
MATPARSE M7 FROM 'a':@FM:'b':@FM:'c':@FM:'d':@FM:'' SETTING N
CRT 7:' ':N:' [':M7(4):']'
CRT M7(0):'|':M7(1):'|':M7(2):'|':M7(3):'|':M7(4)
DIM M8(4)
MAT M8 = 'z'
MATPARSE M8 FROM 'a':@FM:'b' SETTING N
CRT 8:' ':N:' [':M8(3):'][':M8(4):']'
CRT M8(0):'|':M8(1):'|':M8(2):'|':M8(3):'|':M8(4)
DIM M9(4)
MAT M9 = 'z'
MATPARSE M9 FROM 'a b c' USING ' ' SETTING N
CRT 9:' ':N
CRT M9(0):'|':M9(1):'|':M9(2):'|':M9(3):'|':M9(4)
DIM M10(4)
MAT M10 = 'z'
MATPARSE M10 FROM 'a  b' USING ' ' SETTING N
CRT 10:' ':N:' [':M10(2):']'
CRT M10(0):'|':M10(1):'|':M10(2):'|':M10(3):'|':M10(4)
DIM M11(4)
MAT M11 = 'z'
MATPARSE M11 FROM 'abc' USING '' SETTING N
CRT 11:' ':N:' [':M11(1):']'
CRT M11(0):'|':M11(1):'|':M11(2):'|':M11(3):'|':M11(4)
DIM M12(4)
MAT M12 = 'z'
MATPARSE M12, 2, 3 FROM 'a':@FM:'b':@FM:'c' SETTING N
CRT 12:' ':N:' [':M12(1):'][':M12(2):'][':M12(3):']'
CRT M12(0):'|':M12(1):'|':M12(2):'|':M12(3):'|':M12(4)
