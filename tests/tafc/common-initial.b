* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 3: COMMON starts at 0 and is assigned.
COMMON /LAB/ A, B
COMMON C
CRT '[':A:'] [':C:'] ':ASSIGNED(A):' ':ASSIGNED(C):' ':LEN(A)
