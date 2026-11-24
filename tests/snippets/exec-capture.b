EXEC = "printf 'output\n'; printf 'error\n' >&2; exit 7"
EXEC EXEC SETTING Result CAPTURING Output
CRT Output
CRT Result
CRT @SYSTEM.RETURN.CODE
EXEC "printf 'visible\n'"
CRT @SYSTEM.RETURN.CODE
