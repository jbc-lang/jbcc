* CONVERT on a target assigned later, as in T24 R19 IN2BMT.
IF @SENTENCE[' ', 2, 1] = '1' THEN
   CONVERT ',.' TO '.,' IN Display
END
Display = '1,5'
CRT Display
