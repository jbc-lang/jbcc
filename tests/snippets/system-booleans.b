EQU TRUE TO 8, FALSE TO 9
Enabled = @TRUE
Disabled = @FALSE
PRINT Enabled, Disabled, TRUE, FALSE
PRINT 10 + @TRUE - @FALSE
IF Enabled THEN PRINT 'enabled'
IF Disabled THEN PRINT 'wrong' ELSE PRINT 'disabled'
BEGIN CASE
CASE @FALSE
    Result = 'wrong'
CASE @TRUE
    Result = 'default'
END CASE
PRINT Result
