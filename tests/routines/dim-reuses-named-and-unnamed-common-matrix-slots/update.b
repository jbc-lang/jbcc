SUBROUTINE UPDATE()
COMMON Shared(2)
COMMON /CACHE/ Table(2,3), Last
Shared(2) := '!'
Table(2,3) := '!'
Last := '!'
