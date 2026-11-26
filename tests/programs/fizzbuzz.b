EQUATE limit TO 100

FOR number = 1 TO limit
  text = ''
  IF MOD(number, 3) EQ 0 THEN text := 'Fizz'
  IF MOD(number, 5) EQ 0 THEN text := 'Buzz'
  IF text EQ '' THEN text = number
  CRT text
NEXT number
