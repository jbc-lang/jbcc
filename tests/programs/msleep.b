* MSLEEP as in T24 R19 EB.SERVICE job waits (MSLEEP 100).
Duration = @SENTENCE[' ',2,1]
IF Duration = '' THEN MSLEEP ELSE MSLEEP Duration
CRT 'awake'
