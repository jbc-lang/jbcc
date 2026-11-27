* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: FIELD and GROUP edge cases. Multi-byte
* delimiters with a count above 1 are left out: TAFC's results for them
* follow no consistent rule (see the plan).
S = '123:-456:-789'
FOR I = -1 TO 4 ; CRT I:' [':FIELD(S, ':-', I):']' ; NEXT I
CRT '[':FIELD('ab12ab34ab', 'ab', 2):']'
CRT '[':FIELD('a::b::c', '::', 2):'] [':GROUP('a::b::c', '::', 2, 1):']'
CRT '[':FIELD('x:y:z', '', 1):'] [':FIELD('x:y:z', ':', 2, 0):'] [':GROUP('a-b-c', '-', 2, 5):']'
