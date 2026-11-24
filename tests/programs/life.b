EQUATE width TO 40
EQUATE height TO 30

* Leave a border of dead cells around the visible board.
DIM board(width + 1, height + 1), next_board(width + 1, height + 1)
MAT board = 0
MAT next_board = 0

* A glider and a blinker.
board(3, 2) = 1
board(4, 3) = 1
board(2, 4) = 1
board(3, 4) = 1
board(4, 4) = 1

board(19, 15) = 1
board(20, 15) = 1
board(21, 15) = 1

CRT @(-1):
LOOP
  GOSUB draw_board
  IF SYSTEM(14) GT 0 THEN
    key = KEYIN()
    IF key EQ 'q' THEN STOP
  END
  SLEEP 0.2
  GOSUB advance_board
REPEAT

draw_board:
  CRT @(-2):
  FOR y = 1 TO height
    row = ''
    FOR x = 1 TO width
      IF board(x, y) THEN
        row := 'O'
      END ELSE
        row := '.'
      END
    NEXT x
    IF y LT height THEN CRT row ELSE CRT row:
  NEXT y
  RETURN

advance_board:
  FOR y = 1 TO height
    FOR x = 1 TO width
      neighbors = board(x - 1, y - 1) + board(x, y - 1) + board(x + 1, y - 1) \
                + board(x - 1, y)                         + board(x + 1, y) \
                + board(x - 1, y + 1) + board(x, y + 1) + board(x + 1, y + 1)
      next_board(x, y) = 0
      IF (neighbors EQ 3) OR ((neighbors EQ 2) AND board(x, y)) THEN
        next_board(x, y) = 1
      END
    NEXT x
  NEXT y
  MAT board = MAT next_board
  RETURN
