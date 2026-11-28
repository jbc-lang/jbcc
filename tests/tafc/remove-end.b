* tafc-emulation: prime
* TAFC-CROSSCHECK.md: past the end of its list, REMOVE gives '' and 0.
L = "ServiceLevel" : @VM : "PurposeCode"
C = L
FOR I = 1 TO 4
    REMOVE X FROM C SETTING P
    CRT I : " [" : X : "] " : P
NEXT I
D = "one"
FOR I = 1 TO 3
    REMOVE X FROM D SETTING P
    CRT "D" : I : " [" : X : "] " : P
NEXT I
