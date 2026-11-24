EQUATE ROTATION TO 1
Encoded = ENCRYPT('Abc Nop 123!', 'unused', ROTATION)
CRT Encoded
CRT DECRYPT(Encoded, '', ROTATION)
CRT '[':ENCRYPT('', '', ROTATION):']'
