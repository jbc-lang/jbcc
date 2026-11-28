* tafc-emulation: prime
* TAFC-CROSSCHECK.md: dynamic-array indices and matrix subscripts that are
* not positive integers, as T24 code passes them from unassigned or text
* variables.
X = "A" : @FM : "B" : @VM : "C"
I = ""
CRT "empty <" : X<I> : ">"
CRT "decimal <" : OCONV(X<"2.7">, "MCP") : ">"
CRT "text <" : X<"ABC"> : "> <" : X<"1A"> : ">"
CRT "blank <" : OCONV(X<" 2">, "MCP") : ">"
CRT "-1 <" : X<-1> : ">"
CRT "2,0 <" : OCONV(X<2,0>, "MCP") : "> <" : OCONV(X<2, I>, "MCP") : ">"
Y = X ; Y<0> = "Z" ; CRT "0: " : OCONV(Y, "MCP")
Y = X ; Y<I> = "Z" ; CRT "empty: " : OCONV(Y, "MCP")
Y = X ; Y<0,1> = "Q" ; CRT "0,1: " : OCONV(Y, "MCP")
Y = X ; Y<2,0> = "R" ; CRT "2,0: " : OCONV(Y, "MCP")
Y = X ; Y<1,0,0> = "S" ; CRT "1,0,0: " : OCONV(Y, "MCP")
Y = "" ; Y<0> = "T" ; CRT "empty 0: " : OCONV(Y, "MCP")
Y = X ; Y<"2.9", "1.5"> = "U" ; CRT "2.9,1.5: " : OCONV(Y, "MCP")
DIM M(3)
M(1) = "m"
M(2) = "n"
CRT "M('') <" : M(I) : "> M('2.7') <" : M("2.7") : "> M(' 1') <" : M(" 1") : ">"
* A negative subscript reads element 1, in local and COMMON matrices.
COM /PROBE/ R(5)
R(1) = "one"
R(2) = "two"
CRT "R(-1) <" : R(-1) : "> R(-10) <" : R(-10) : "> M(-3) <" : M(-3) : ">"
