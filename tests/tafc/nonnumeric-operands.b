* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 3: numeric text forms and nonnumeric operands.
CRT '[':'' + 1:'] [':'-' + 1:'] [':'.' + 2:'] [':'+5' + 0:'] [':'5.' + 0:'] [':'.5' + 0:']'
CRT '[':' 5' + 1:'] [':'5 ' + 1:']'
CRT 'abc' * 2
CRT '1E3' + 0
CRT '1]2' + 1
A = 'x' ; A += 1 ; CRT A
CRT 'end'
