Command = "printf 'one\n\nthree\n'; printf 'diagnostic\n' >&2; exit 3"
EXECUTE Command CAPTURING Command
CRT Command
DIM Result(2)
PERFORM "printf 'unterminated'" CAPTURING Result(2)
CRT Result(2)
PERFORM ':' CAPTURING Command
CRT '[' : Command : ']'
