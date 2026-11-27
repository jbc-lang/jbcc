* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: @(-n) and cursor codes for TERM=vt100.
FOR I = 1 TO 30
   X = @(-I)
   IF X NE '' THEN CRT -I:'=':OCONV(X, 'MX')
NEXT I
CRT 'col5=':OCONV(@(5), 'MX'):' 5,3=':OCONV(@(5,3), 'MX'):' 0,0=':OCONV(@(0,0), 'MX')
