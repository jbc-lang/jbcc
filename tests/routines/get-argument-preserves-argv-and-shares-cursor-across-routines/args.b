GET (ARG.) First THEN CRT First ELSE ABORT
CALL GET.MORE
Keep = 'previous'
GET(ARG., 99) Keep ELSE CRT Keep
GET(ARG.) Next THEN
    CRT Next
END ELSE ABORT
GET(ARG.) Exhausted THEN ABORT
CRT '[':Exhausted:']'
GET(ARG., 1) Again
CRT Again
