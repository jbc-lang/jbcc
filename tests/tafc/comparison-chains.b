* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: spaced comparison chains. TAFC reads
* "2 < 3 > 0" as the extraction 2<3> and an implicit format, so it prints 0;
* jbcc keeps a comparison chain (README, "Implemented subset").
CRT 2 < 3 > 0, 2 < 3 >= 0, 1 < 2 < 3, 3 > 2 > 1
A = 5 ; B = 7
CRT A < B > 0, A > B < 1
