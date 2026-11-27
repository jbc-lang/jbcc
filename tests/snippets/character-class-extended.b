* Guide ISCNTRL example: CR, LF and @FM are control characters.
V.STRING = CHAR(13) : CHAR(10)
CRT ISCNTRL(V.STRING)
V.STRING = @FM : V.STRING
CRT ISCNTRL(V.STRING)
CRT ISCNTRL('A':CHAR(10)):ISCNTRL('')
* Guide ISPRINT note: a trailing @FM is not printable.
CRT ISPRINT('cawerc' :@FM):ISPRINT('a b~'):ISPRINT('')
CRT ISGRAPH('a!b'):ISGRAPH('a b')
CRT ISPUNCT('!?,.'):ISPUNCT('a!')
CRT ISXDIGIT('09afAF'):ISXDIGIT('0x1')
