OPEN 'CUSTOMERS' TO F ELSE STOP
OPEN 'CUSTOMERS' ELSE STOP
DIM A(2,2)
MAT A = 'old'
Record = 'a' : @FM : '' : @FM : 'b' : @VM : 'c' : @FM : 'd' : @FM : 'e' : @FM
WRITE Record TO F,'key'
MATREAD A FROM F,'key' SETTING Count THEN PRINT Count ELSE STOP
PRINT A(1,1), LEN(A(1,2)), A(2,1)<1,2>, CONVERT(A(2,2),@FM,'|')
DELETE F,'key'
MATREAD A FROM 'key' SETTING Count ON ERROR STOP ELSE PRINT Count,A(1,1),A(2,2)<2>
WRITE 'short' TO F,'key'
MATREAD A FROM 'key' SETTING Count ELSE STOP
PRINT Count,A(1,1),LEN(A(2,2))
WRITE '' TO F,'empty'
MATREAD A FROM F,'empty' SETTING Count THEN PRINT Count,LEN(A(1,1)) ELSE STOP
MAT A = 'kept'
MATREAD A FROM 'CUSTOMERS','key' SETTING Count ON ERROR
   PRINT 'unexpected error'
END ELSE
   PRINT Count,A(1,2)
END
