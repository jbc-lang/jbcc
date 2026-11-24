GET(ARG.) Mode
Problem = ''
IF Mode = 'hit' THEN
    Value = 'ready'
END ELSE
    IF Mode = 'skip' THEN Problem = 'missing'
END
IF NOT(Problem) THEN CRT Value ELSE CRT Problem
