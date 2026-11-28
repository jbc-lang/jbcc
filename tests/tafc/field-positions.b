* tafc-emulation: prime
* TAFC-CROSSCHECK.md: a FIELD position or count that is empty or below 1
* means 1, and a fraction truncates. A text position varies between runs
* in TAFC; jbcc takes it as 1.
S = "a b c d"
E = ""
CRT "FIELD empty [" : FIELD(S, " ", E) : "]"
CRT "FIELD frac [" : FIELD(S, " ", "2.7") : "]"
CRT "FIELD count empty [" : FIELD(S, " ", 2, E) : "]"
CRT "FIELD zero [" : FIELD(S, " ", 0) : "]"
CRT "FIELD neg [" : FIELD(S, " ", -1) : "]"
L = "a" : @FM : "b" : @FM : "c"
CRT "GROUP empty [" : CHANGE(L[@FM, 2, E], @FM, "^") : "]"
CRT "GROUP neg [" : CHANGE(L[@FM, 2, -1], @FM, "^") : "]"
