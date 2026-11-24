GET(ARG.) Mode
IF Mode = 'hit' THEN List = 'first':@FM:'second'
REMOVE Piece FROM List SETTING Code
CRT Piece, Code
Piece = REMOVE(List, Code)
CRT Piece, Code
REMOVE Piece FROM List SETTING Code
CRT Piece, Code
