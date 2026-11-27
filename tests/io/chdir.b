* CHDIR as a condition, as in T24 R13 SEAT.SCRIPT.ACTIVITY.TRANSFER and
* the guide's CHDIR example. The test supplies the sub directory. GETCWD as
* in T24 R19 IF GETCWD(HOMEDIR) THEN.
IF CHDIR('sub') THEN CRT 'in sub' ELSE CRT 'no sub'
IF GETCWD(Here) THEN CRT 'cwd known' ELSE CRT 'no cwd'
OSWRITE 'x' ON 'marker'
IF CHDIR('missing') ELSE CRT 'missing kept sub'
CRT CHDIR(''), CHDIR('..')
OSWRITE 'y' ON 'top'
IF GETCWD(Top) THEN CRT Here[LEN(Top) + 1, 99]
