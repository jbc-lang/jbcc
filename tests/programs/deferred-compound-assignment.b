GET(ARG.) Mode
IF Mode = 'add' THEN
    Count += 1
END
IF Mode = 'append' THEN
    Text := '!'
END
CRT 'done'
