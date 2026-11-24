CALL SNAPSHOT(Before)
OPEN 'F' TO F ELSE ABORT
WRITE 'new' TO F,'one'
WRITEU 'updated' TO F,'one'
WRITEV 'tail' TO F,'one',2
DIM A(1)
A(1) = 'matrix'
MATWRITE A TO F,'two'
WRITE 'blocked' TO F,'held' ON ERROR NULL
DELETE F,'two'
CALL SNAPSHOT(After)
CRT Before<20>:':':After<20>:':':DCOUNT(After,@FM)
CRT After<1>:':':After<2>:':':After<4>
CRT After<3>
CRT After<5>:':':After<6>:':':After<8>:':':After<10>
CRT '[':After<7>:']:[':After<19>:']'
CRT After<41>
CRT After<42>
CRT After<43>
