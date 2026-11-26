SUBROUTINE SHOW.LINKED
COMMON /SHARED/ Count, Linked
DIM Linked(3)
CRT Linked(1) : '|' : Linked(2) : '|' : Linked(3)
Count += 1
RETURN
END
