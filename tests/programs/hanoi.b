EQUATE disks TO 4

* GOSUB has no local variables, so each level of recursion saves its
* arguments here before moving the smaller tower out of the way.
DIM saved_count(disks), saved_from(disks), saved_to(disks), saved_via(disks)
depth = 0
moves = 0

count = disks
from = 'A'
to = 'C'
via = 'B'
GOSUB move_tower

CRT moves:' moves'
STOP

move_tower:
  IF count EQ 0 THEN RETURN
  depth += 1
  saved_count(depth) = count
  saved_from(depth) = from
  saved_to(depth) = to
  saved_via(depth) = via

  * Move the smaller tower onto the spare peg.
  count = saved_count(depth) - 1
  from = saved_from(depth)
  to = saved_via(depth)
  via = saved_to(depth)
  GOSUB move_tower

  moves += 1
  CRT 'Move disk ':saved_count(depth):' from ':saved_from(depth):' to ':saved_to(depth)

  * Move the smaller tower from the spare peg onto the largest disk.
  count = saved_count(depth) - 1
  from = saved_via(depth)
  to = saved_to(depth)
  via = saved_from(depth)
  GOSUB move_tower

  depth -= 1
  RETURN
