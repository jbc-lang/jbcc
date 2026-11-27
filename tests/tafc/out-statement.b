* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: OUT writes one byte, modulo 256.
FOR I = 72 TO 74 ; OUT I ; NEXT I
OUT 256+65
OUT 10
