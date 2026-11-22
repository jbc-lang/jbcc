A = 'ABC' : @FM : 'DEF' : @VM : '123' : @VM : 'XYZ' : @VM : '456'
A := @FM : '789' : @FM : '---' : @SM : 'prefixXYXYsuffix'
FINDSTR 'XY' IN A SETTING F,V THEN PRINT F,V ELSE STOP
DIM Pos(3)
FINDSTR 'XY' IN A,2 SETTING Pos(1),Pos(2),Pos(3) ELSE STOP
PRINT Pos(1),Pos(2),Pos(3)
FINDSTR 'XY' IN A,3 SETTING Pos(1) THEN STOP ELSE PRINT 'no third element',Pos(1)
FINDSTR 'xy' IN A SETTING F THEN STOP ELSE PRINT 'case-sensitive'
Key = 'C' : @FM : 'D'
FINDSTR Key IN A SETTING F THEN STOP ELSE PRINT 'separate fields'
FINDSTR 'suffix' IN A<4> SETTING F,V,S THEN PRINT F,V,S
FINDSTR '' IN 'a' : @VM : '',2 SETTING F,V THEN PRINT F,V
