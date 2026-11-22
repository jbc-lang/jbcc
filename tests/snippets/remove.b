R = 'a' : CHAR(255) : @FM : 'c' : @VM : 'd' : @SM : 'e' : CHAR(251) : 'f' : CHAR(250) : 'g' : CHAR(249) : 'tail'
LOOP
  REMOVE Item FROM R SETTING Mark
  PRINT '[' : Item : '] ' : Mark
WHILE Mark
REPEAT
Item = 'unchanged'
REMOVE Item FROM R SETTING Mark
PRINT Item, Mark
R = R
REMOVE Item FROM R SETTING Mark
PRINT Item, Mark
Copy = R
REMOVE Item FROM Copy SETTING Mark
PRINT Item, Mark
DIM M(1)
MAT M = 'x' : @VM
REMOVE Item FROM M(0) SETTING Mark
PRINT Item, Mark
REMOVE Item FROM M(0) SETTING Mark
PRINT '[' : Item : ']', Mark
REMOVE M(0) FROM M(1) SETTING Mark
PRINT M(0), Mark
M(0) = ''
REMOVE Item FROM M(0) SETTING Mark
PRINT '[' : Item : ']', Mark
