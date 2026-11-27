* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: LOCK, PROCREAD, RQM, PAUSE and WAKE alone.
LOCK 5 THEN CRT 'locked 5' ELSE CRT 'busy 5'
LOCK 5 THEN CRT 'locked again' ELSE CRT 'busy again'
UNLOCK 5
UNLOCK
PROCREAD X THEN CRT 'procread then' ELSE CRT 'procread else'
PROCWRITE 'abc'
PROCREAD X THEN CRT 'procread then' ELSE CRT 'procread else'
RQM 0
PAUSE 1
CRT 'paused'
INPUTNULL '&'
CRT 'done'
