Note = 'batch'
IF 0 THEN TRANSABORT ELSE ABORT
CRT Note
TRANSABORT 'rollback' ELSE CRT 'failure'
CRT 'after'
