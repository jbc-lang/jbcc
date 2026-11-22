OPEN 'CUSTOMERS' TO F ELSE STOP
OPEN 'MISSING' TO Bad THEN PRINT 'wrong' ELSE PRINT 'missing file'
WRITE 'no' ON Bad, '1' ELSE PRINT 'write failed'
READ R FROM F, '1' ELSE PRINT 'missing record'
FOR I = 1 TO 2
    WRITE 'record' : I TO F, '1' THEN PRINT 'saved' : I
NEXT
READ R FROM F, '1' THEN PRINT R
WRITE '' TO F, '1'
READ E FROM F, '1' THEN PRINT 'empty=' : LEN(E)
PRINT R
