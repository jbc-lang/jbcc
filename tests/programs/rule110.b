EQUATE width TO 63
EQUATE generations TO 32

* The extra cell at each end stays dead.
DIM cells(width + 1), next_cells(width + 1)
MAT cells = 0
MAT next_cells = 0
cells((width + 1) / 2) = 1

* Rule 110 in binary, ordered from neighborhood 111 down to 000.
rule = '01101110'

FOR generation = 1 TO generations
  row = ''
  FOR x = 1 TO width
    IF cells(x) THEN
      row := '#'
    END ELSE
      row := '.'
    END

    neighborhood = 4 * cells(x - 1) + 2 * cells(x) + cells(x + 1)
    next_cells(x) = rule[8 - neighborhood, 1]
  NEXT x
  CRT row
  MAT cells = MAT next_cells
NEXT generation
