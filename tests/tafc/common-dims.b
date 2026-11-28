* tafc-emulation: prime
* TAFC-CROSSCHECK.md: a COMMON matrix keeps the dimensions it was first
* given; units that declare it larger or smaller share it, and the members
* after it line up.
COMMON /PRBC/ C(3), K
C(2) = "c2"
C(3) = "c3"
K = "k"
CALL PRBCOM
CALL PRBSMALL
CRT "main [" : C(2) : "][" : K : "]"
* tafc-subroutine: PRBCOM
SUBROUTINE PRBCOM
COMMON /PRBC/ D(5), L
CRT "large [" : D(2) : "][" : D(3) : "][" : L : "]"
D(2) = "d2"
RETURN
END
* tafc-subroutine: PRBSMALL
SUBROUTINE PRBSMALL
COMMON /PRBC/ E(2), M
CRT "small [" : E(2) : "][" : E(3) : "][" : M : "]"
RETURN
END
