Note = 'batch'
IF 0 THEN TRANSABORT ELSE ABORT
CRT Note
TRANSEND Note THEN
    CRT 'success'
END ELSE CRT 'failure'
CRT 'after'
