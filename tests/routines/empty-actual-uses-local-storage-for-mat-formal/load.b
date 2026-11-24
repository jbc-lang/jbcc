SUBROUTINE LOAD.VALUES(MAT Items, Size, Answer)
DIM Items(Size)
MAT Items = 'filled'
Answer = INMAT(Items):':':Items(Size)
