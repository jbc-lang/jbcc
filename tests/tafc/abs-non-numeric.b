* tafc-emulation: prime
* TAFC-CROSSCHECK.md: ABS of '' and of text that is not a number, as T24
* code passes unassigned or text amounts.
E = ""
T = "X1"
CRT "abs <" : ABS(E) : "> <" : ABS(T) : "> <" : ABS("-2.5") : "> <" : ABS(" -3 ") : ">"
