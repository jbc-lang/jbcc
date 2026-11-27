* NOTS and LENS as in T24 R19 IF NOT(INDEX(NOTS(Rec),"0",1)) and
* SUM(LENS(List)); NOTS values from the guide's example.
X = 5 ; Y = 5
CRT CHANGE(NOTS(X-Y :@VM: X+Y), @VM, ']')
CRT CHANGE(CHANGE(CHANGE(NOTS('' :@FM: 'a' :@VM: 0 :@SM: ' '), @FM, '^'), @VM, ']'), @SM, '\')
CRT CHANGE(CHANGE(LENS('abc':@VM:'':@SM:'de  '), @VM, ']'), @SM, '\'), LENS(''), SUM(LENS('ab':@VM:'c'))
IF NOT(INDEX(NOTS(1:@VM:2), '0', 1)) THEN CRT 'none set' ELSE CRT 'some set'
* FSUB as in T24 R19 FSUB(DIV.VALUE, FINAL.VALUE); the guide's example.
PRECISION 7
CRT FSUB(2.54, 5.703358), 2.54 - 5.703358
PRECISION 4
CRT FSUB(10, 0.00004), FSUB(1, 1)
