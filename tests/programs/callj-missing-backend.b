CALLJ = 'hello'
IF 0 THEN
    CALLJ 'example.Tools', '$format', CALLJ SETTING Response ON ERROR
        ABORT
    END
END
CRT CALLJ
CALLJ 'example.Tools', 'format', CALLJ:'!' SETTING Response ON ERROR CRT 'handler'
CRT Response
