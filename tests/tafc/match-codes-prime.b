* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 1: MATCHES pattern codes under prime.
T = 'abc' ; P = '...' ; GOSUB SHOW
T = '' ; P = '...' ; GOSUB SHOW
T = 'abc' ; P = 'a...' ; GOSUB SHOW
T = 'abc' ; P = '...c' ; GOSUB SHOW
T = 'abc' ; P = 'a...c' ; GOSUB SHOW
T = 'ac' ; P = 'a...c' ; GOSUB SHOW
T = 'a.b' ; P = "'a'...'b'" ; GOSUB SHOW
T = 'a..b' ; P = 'a..b' ; GOSUB SHOW
T = 'axxb' ; P = 'a..b' ; GOSUB SHOW
T = 'axb' ; P = 'a.b' ; GOSUB SHOW
T = 'a.b' ; P = 'a.b' ; GOSUB SHOW
T = 'abcd' ; P = 'a....' ; GOSUB SHOW
T = '5C' ; P = '5C' ; GOSUB SHOW
T = '2HQJ4' ; P = '5C' ; GOSUB SHOW
T = 'C' ; P = '1C' ; GOSUB SHOW
T = 'ab12' ; P = '2a2n' ; GOSUB SHOW
T = 'ab12' ; P = '4x' ; GOSUB SHOW
T = 'JOHN' ; P = 'JOHN' ; GOSUB SHOW
T = 'john' ; P = 'JOHN' ; GOSUB SHOW
T = 'JOHN' ; P = 'J3A' ; GOSUB SHOW
T = 'ab' ; P = '1A...1A' ; GOSUB SHOW
T = 'a1b' ; P = '1A0N1A' ; GOSUB SHOW
T = 'a-b' ; P = "1A'-'1A" ; GOSUB SHOW
T = 'x' ; P = '0X' ; GOSUB SHOW
T = 'AB' ; P = '2A':@VM:'2N' ; GOSUB SHOW
T = '12' ; P = '2A':@VM:'2N' ; GOSUB SHOW
T = '2022/08/31' ; P = "2-4N'/'2N'/'2N" ; GOSUB SHOW
T = 'abc' ; P = '1-2A' ; GOSUB SHOW
T = 'ab cd' ; P = '...' : ' ' : '...' ; GOSUB SHOW
T = '12AB' ; P = '2N...' ; GOSUB SHOW
T = 'x...y' ; P = "'x...y'" ; GOSUB SHOW
T = '9.99' ; P = "0N'.'2N" ; GOSUB SHOW
T = '.99' ; P = "0N'.'2N" ; GOSUB SHOW
T = 'AB12CD' ; F = MATCHFIELD(T, '2A...2A', 2) ; CRT 'MATCHFIELD [':F:']'
T = 'AB12CD' ; F = MATCHFIELD(T, '2A2N2A', 2) ; CRT 'MATCHFIELD2 [':F:']'
STOP
SHOW:
CRT DQUOTE(T):' MATCHES ':DQUOTE(CHANGE(P, @VM, ']')):' = ':(T MATCHES P)
RETURN
