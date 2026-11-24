OSDELETE 'missing' SETTING S ON ERROR
    CRT S:':':STATUS()
END
OSDELETE 'missing' SETTING S
CRT 'unreachable'
