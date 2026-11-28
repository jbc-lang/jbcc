* tafc-emulation: prime
* TAFC-CROSSCHECK.md: DIM of a MAT parameter keeps the caller's matrix and
* its dimensions; PRBDIM reads A(3) past its own DIM X(2).
DIM A(3)
A(1) = "a" ; A(2) = "b" ; A(3) = "c"
CALL PRBDIM(MAT A)
CRT "after [" : A(1) : "][" : A(3) : "]"
* tafc-subroutine: PRBDIM
SUBROUTINE PRBDIM(MAT X)
DIM X(2)
CRT "in [" : X(1) : "][" : X(3) : "]"
X(3) = "three"
RETURN
END
