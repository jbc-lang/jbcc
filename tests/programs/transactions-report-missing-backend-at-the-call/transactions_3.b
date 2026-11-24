Note = 'batch'
IF 0 THEN TRANSABORT ELSE ABORT
CRT Note
TRANSTART SYNC 'start':Note THEN CRT 'success' ELSE CRT 'failure'
CRT 'after'
