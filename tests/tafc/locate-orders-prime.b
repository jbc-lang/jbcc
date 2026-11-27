* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 1: LOCATE BY orders, inserting at each position.
L = 5:@FM:10:@FM:9:@FM:100:@FM:1:@FM:'B':@FM:'a':@FM:-3:@FM:'':@FM:2.5:@FM:'b2':@FM:'b10'
FOR N = 1 TO 6
   ORDER = FIELD('AL,AR,AN,DL,DR,DN', ',', N)
   A = ''
   FOR I = 1 TO DCOUNT(L, @FM)
      LOCATE L<I> IN A BY ORDER SETTING P ELSE NULL
      INS L<I> BEFORE A<P>
   NEXT I
   CRT ORDER:' ':CHANGE(A, @FM, ',')
NEXT N
