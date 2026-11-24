SUBROUTINE RESET(Argument, MAT Items, Flag)
COMMON /STATE/ Shared, Cache(2)
COMMON Unnamed
N = 2
DIM Fixed(2), Ready(N)
IF 0 THEN DIM Deferred(N)
Fixed(1) = 'discard'
Ready(2) = 'discard'
IF Flag THEN
    CLEAR
    CRT (IF 1 THEN Late ELSE 'bad'):':':Fixed(1):':':Ready(2):':':Ready(0)
    CRT Shared:':':Unnamed:':':Cache(1):':':Items(0):':':Argument
END ELSE
    Local = 9
END
CRT Local
