X = 0
CALL ADD.IT$(X)
CALL !ADD.IT$(X); ! trailing comment
IF 0!X THEN CALL !ADD.IT$(X)
!ADD.IT$(X) is a comment here
CRT X
