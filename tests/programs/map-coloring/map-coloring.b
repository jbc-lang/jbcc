* Greedy map coloring, ported from tests/map/test.easy of the Easy
* language compiler (https://github.com/begoon/easy).
*
* Standard input holds the number of nodes, then for each node its id,
* its number of neighbours, its name and the ids of its neighbours, and
* finally 0. Tokens are separated by spaces or line breaks. The program
* prints the adjacency matrix, then gives each node the lowest color that
* none of its already colored neighbours has, and lists the nodes of each
* color.

token_line = ''
token = ''

GOSUB next_token
node_number = token
IF node_number LT 1 THEN
  CRT 'ERROR: number of nodes must be 1 or greater'
  STOP
END

DIM ids(node_number), colors(node_number), available(node_number)
DIM adjacency(node_number, node_number)
MAT adjacency = 0

CRT 'NUMBER OF NODES ' : node_number
CRT

FOR i = 1 TO node_number
  GOSUB next_token
  ids(i) = token
  GOSUB next_token
  neighbour_number = token
  * The name is read but not printed.
  GOSUB next_token
  FOR j = 1 TO neighbour_number
    GOSUB next_token
    adjacency(ids(i), token) = 1
  NEXT
  * The Easy program writes a carriage return after each node, and the
  * expected output keeps it.
  CRT CHAR(13):
NEXT

GOSUB next_token
IF token NE 0 THEN
  CRT 'ERROR: expected 0 at the end of input'
  STOP
END

GOSUB print_matrix
GOSUB color_nodes
GOSUB print_colors
STOP

* Read the next token from standard input into token.
next_token:
  LOOP
  WHILE token_line EQ ''
    INPUT token_line
    token_line = TRIM(token_line)
  REPEAT
  token = FIELD(token_line, ' ', 1)
  token_line = token_line[LEN(token) + 2, LEN(token_line)]
  RETURN

print_matrix:
  CRT 'ADJACENCY MATRIX:'
  CRT
  line = '    '
  FOR i = 1 TO node_number
    line := MOD(i, 10)
  NEXT
  CRT line
  CRT '    ' : STR('-', node_number)
  FOR i = 1 TO node_number
    line = ''
    IF i LT 10 THEN line = ' '
    line := i : '| '
    FOR j = 1 TO node_number
      IF adjacency(i, j) THEN line := '*' ELSE line := ' '
    NEXT
    CRT line
  NEXT
  RETURN

* Node 1 takes color 1. Each later node takes the lowest color that no
* colored neighbour has.
color_nodes:
  MAT colors = -1
  colors(1) = 1
  max_color = 1
  MAT available = 1
  FOR i = 2 TO node_number
    FOR j = 1 TO node_number
      IF adjacency(i, j) AND colors(j) NE -1 THEN available(colors(j)) = 0
    NEXT
    found = 0
    FOR j = 1 TO node_number UNTIL found
      IF available(j) THEN
        colors(i) = j
        IF j GT max_color THEN max_color = j
        found = 1
      END
    NEXT
    MAT available = 1
  NEXT
  RETURN

print_colors:
  CRT
  CRT 'NUMBER OF COLORS NEEDED: ' : max_color
  CRT
  FOR color = 1 TO max_color
    line = 'COLOR ' : color : ', NODES: '
    FOR i = 1 TO node_number
      IF colors(i) EQ color THEN line := ids(i) : ' '
    NEXT
    CRT line
  NEXT
  RETURN
