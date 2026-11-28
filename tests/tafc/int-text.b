* tafc-emulation: prime
* TAFC-CROSSCHECK.md: INT of text that is not a number keeps its leading
* sign and digits; INT('') is 0.
X = "abc"
CRT "INT text [" : INT(X) : "]"
Y = ""
CRT "INT empty [" : INT(Y) : "]"
Z = "12abc"
CRT "INT mixed [" : INT(Z) : "]"
DIM V(8)
V(1) = "1.5x" ; V(2) = "-3.7q" ; V(3) = "x5" ; V(4) = " 7" ; V(5) = "7 " ; V(6) = "-0x" ; V(7) = "." ; V(8) = "-"
FOR I = 1 TO 8
   CRT "INT " : I : " [" : INT(V(I)) : "]"
NEXT I
S = "HELLOWORLD"
E = ""
