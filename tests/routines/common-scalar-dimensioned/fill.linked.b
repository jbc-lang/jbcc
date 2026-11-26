SUBROUTINE FILL.LINKED
COMMON /SHARED/ Count, Linked
First = 'one'
DIM Linked(3)
* A local scalar after the DIM gets its own frame field.
Last = 'three'
MAT Linked = ''
Linked(1) = First
Linked(3) = Last
Count += 1
RETURN
END
