OPEN 'BOOKS' TO File ELSE ABORT
DIM Handles(2)
Handles(1) = File
IF 0 THEN CRT INDICES(File)<1>
CRT 'before'
CRT INDICES(Handles(1), 'BY.':'TITLE')
CRT 'after'
