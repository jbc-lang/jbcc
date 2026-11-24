X = 4
R<1,2> = 3
CALL MIX(X + 1, ;* capture the first argument

    * pass X twice by reference
    X,
    ! extract from a dynamic array
    R<1,
      2>,
    X)
CRT X
