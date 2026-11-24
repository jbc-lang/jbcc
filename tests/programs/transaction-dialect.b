GET(ARG.) Operation
BEGIN CASE
CASE Operation = 'start'
    TRANSACTION START THEN CRT 'started' ELSE CRT 'start failed'
CASE Operation = 'commit'
    TRANSACTION COMMIT ELSE CRT 'commit failed'
CASE Operation = 'abort'
    TRANSACTION ABORT
END CASE
CRT 'done'
