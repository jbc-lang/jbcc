SUBROUTINE STORE(First)
N = 2
IF First THEN
    DIM Rows(N,3)
    Rows(2,3) = 'first'
END ELSE
    DIMENSION Rows(2,3)
    Rows(2,3) = 'second'
END
DIM Rows(2,3)
DIM Rows(N,3)
CRT Rows(2,3)
DIM Fixed(2)
Fixed(2) = Rows(2,3)
DIM Fixed(N)
CRT Fixed(2)
