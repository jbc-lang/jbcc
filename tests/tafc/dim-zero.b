* tafc-emulation: prime
* TAFC-CROSSCHECK.md: a dimension of 0 or '' gives 10 elements, as T24
* code dimensions with COMMON counts (DIM LOCALI(V)) before they are set.
N = 0
DIM A(N)
A(1) = "a"
A(10) = "ten"
CRT "A " : A(1) : " " : A(10)
E = ""
DIM B(E)
B(10) = "b"
CRT "B " : B(10)
