* tafc-emulation: prime
* TAFC-CROSSCHECK.md: CAPTURING drops one final newline. TAFC runs the
* command without a shell; these lines need none.
EXECUTE 'echo a' CAPTURING C ; CRT 1:' [':CHANGE(C, @FM, '|'):']'
EXECUTE 'echo' CAPTURING C ; CRT 2:' [':CHANGE(C, @FM, '|'):']'
EXECUTE 'true' CAPTURING C ; CRT 3:' [':CHANGE(C, @FM, '|'):']'
EXECUTE './LINES' CAPTURING C ; CRT 4:' [':CHANGE(C, @FM, '|'):']'
EXECUTE './NONE' CAPTURING C ; CRT 5:' [':CHANGE(C, @FM, '|'):']'
* tafc-program: LINES
CRT 'a'
CRT ''
CRT ''
* tafc-program: NONE
CRT 'b':
