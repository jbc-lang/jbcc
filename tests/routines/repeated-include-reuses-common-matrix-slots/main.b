N = 3
Count = 0
$INSERT shared.inc
Rows(3,2) = 'row'
Fixed(2) = 'fixed'
Tail = 'tail'
$INSERT shared.inc
CALL CHECK()
CRT Rows(3,2):':':Fixed(2):':':Tail:':':Count
