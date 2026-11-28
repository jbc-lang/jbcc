* tafc-emulation: prime
* TAFC-CROSSCHECK.md: FOR with an empty value, bound or step.
E = ""
N = 0
FOR I = 1 TO E
  N += 1
NEXT I
CRT "empty " : N
FOR J = E TO 2
  N += 1
NEXT J
CRT "from empty " : N
FOR K = 1 TO 3 STEP E
  N += 1
  IF N > 20 THEN EXIT
NEXT K
CRT "step empty " : N
