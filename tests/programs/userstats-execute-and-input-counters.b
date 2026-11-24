Start = @USERSTATS
EXECUTE ':'
EXEC 'exit 7' RETURNING Code
DATA 'command input'
PERFORM 'cat' CAPTURING Captured
CRT Start<23>:':':Start<24>
CRT @USERSTATS<23>:':':Code<1>:':':Captured<1>
PROMPT ''
DATA 'queued'
INPUT Value
INPUT Waited FOR 0 THEN ABORT ELSE CRT Value:':':@USERSTATS<24>
INPUT Ended
CRT '[':Ended:'] ':@USERSTATS<24>
