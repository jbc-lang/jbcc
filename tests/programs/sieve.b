EQUATE limit TO 200
EQUATE per_row TO 10

DIM composite(limit)
MAT composite = 0

* Cross out the multiples of each prime, starting from its square.
FOR candidate = 2 TO limit
  IF NOT(composite(candidate)) THEN
    FOR multiple = candidate * candidate TO limit STEP candidate
      composite(multiple) = 1
    NEXT multiple
  END
NEXT candidate

primes = 0
row = ''
FOR candidate = 2 TO limit
  IF NOT(composite(candidate)) THEN
    primes += 1
    row := FMT(candidate, '5R')
    IF MOD(primes, per_row) EQ 0 THEN
      CRT row
      row = ''
    END
  END
NEXT candidate
IF row NE '' THEN CRT row

CRT primes:' primes up to ':limit
