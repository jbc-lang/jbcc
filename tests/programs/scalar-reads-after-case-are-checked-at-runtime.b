GET(ARG.) Mode
BEGIN CASE
    CASE Mode[1,1] = 'a'
        IF Mode = 'alpha' THEN Value = 'first'
    CASE Mode = 'beta'
        Value = 'second'
END CASE
IF Mode # 'skip' THEN CRT Value
