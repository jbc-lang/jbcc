* tafc-emulation: prime
* TAFC-CROSSCHECK.md: an empty substring start or length, or INS position,
* is 0.
S = "HELLOWORLD"
E = ""
CRT "start empty [" : S[E, 3] : "]"
CRT "len empty [" : S[2, E] : "]"
CRT "both empty [" : S[E, E] : "]"
CRT "one empty [" : S[E] : "]"
CRT "start zero [" : S[0, 3] : "]"
R = "a" : @FM : "b"
INS "new" BEFORE R<E>
CRT "ins empty [" : CHANGE(R, @FM, "^") : "]"
R = "a" : @FM : "b"
INS "new" BEFORE R<2,E>
CRT "ins value empty [" : CHANGE(CHANGE(R, @FM, "^"), @VM, "]") : "]"
R = "a" : @FM : "b"
R = INSERT(R, E; "fn")
CRT "insert fn [" : CHANGE(R, @FM, "^") : "]"
