* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: deterministic SYSTEM keys (TERM=vt100).
FOR K = 2 TO 3 ; CRT K:'=':SYSTEM(K) ; NEXT K
CRT '7=':SYSTEM(7)
FOR K = 35 TO 39 ; CRT K:'=':SYSTEM(K) ; NEXT K
CRT '1017=':SYSTEM(1017)
CRT '12ok=':(SYSTEM(12) >= 0 AND SYSTEM(12) < 86400000)
