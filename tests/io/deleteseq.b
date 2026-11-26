* DELETESEQ forms from the guide's DELETESEQ chapter, as used by
* T24 R13 CLEAR.TOKENS and DW.EXPORT.CONFIGURE (directory and item name).
OSWRITE 'one' ON 'a.txt'
DELETESEQ '.', 'a.txt' THEN CRT 'deleted a' ELSE CRT 'kept a'
OSREAD text FROM 'a.txt' ELSE CRT 'a is gone'
OSWRITE 'two' ON 'b.txt'
DELETESEQ 'b.txt' ELSE CRT 'kept b'
OSREAD text FROM 'b.txt' ELSE CRT 'b is gone'
DELETESEQ '.', 'missing.txt' SETTING code ELSE CRT 'missing ' : code
DELETESEQ '.', 'missing.txt' ON ERROR CRT 'error' LOCKED CRT 'locked' ELSE NULL
* The test makes ro/c.txt in a read-only directory.
DELETESEQ 'ro', 'c.txt' ON ERROR CRT 'cannot delete c' ELSE CRT 'else c'
CRT 'done'
