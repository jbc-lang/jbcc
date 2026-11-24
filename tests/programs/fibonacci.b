current = 0
following = 1

FOR index = 1 TO 20
  CRT current
  next_value = current + following
  current = following
  following = next_value
NEXT index
