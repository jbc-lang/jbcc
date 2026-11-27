* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 3: division by zero warns, gives 0, continues.
* The divisor is a decimal: TAFC prints 0.0nan for an integer variable
* and 0.0inf for the string '0', a formatting quirk not to reproduce.
Z = 0.0
X = 7 / Z
CRT 'x=':X:' len ':LEN(X)
CRT DIVS(10:@VM:9:@VM:8, 2:@VM:Z)
CRT 'mod ':MOD(7, Z):' rem ':REM(7, Z):' div ':DIV(7, Z)
CRT 'end'
