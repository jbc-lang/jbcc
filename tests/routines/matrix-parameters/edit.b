FUNCTION EDIT(MAT M, Alias)
FOR I = 1 TO 2
    M(2,3) = Alias : I
NEXT I
Alias = 'new'
RETURN M(2,3)
