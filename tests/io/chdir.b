* CHDIR as a condition, as in T24 R13 SEAT.SCRIPT.ACTIVITY.TRANSFER and
* the guide's CHDIR example. The test supplies the sub directory.
IF CHDIR('sub') THEN CRT 'in sub' ELSE CRT 'no sub'
OSWRITE 'x' ON 'marker'
IF CHDIR('missing') ELSE CRT 'missing kept sub'
CRT CHDIR(''), CHDIR('..')
OSWRITE 'y' ON 'top'
