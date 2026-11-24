Cmd = "printf 'one\ntwo'; printf 'bad\nworse\n' >&2; exit 7"
EXECUTE Cmd CAPTURING Out RETURNING Status
CRT Out
CRT Status
DIM R(2)
PERFORM Cmd SETTING R(1) CAPTURING R(2)
CRT R(1)
CRT R(2)
EXECUTE "printf 'visible\n'; exit 5" RETURNING Status
CRT Status
PERFORM ':' SETTING Status
CRT Status
PERFORM "printf ignored; exit 2" SETTING Both CAPTURING Both
CRT Both
EXECUTE 'kill -TERM $$' RETURNING Status
CRT Status
