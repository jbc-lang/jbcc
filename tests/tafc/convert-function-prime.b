* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 1: CONVERT(from, to, text) under prime.
CRT CONVERT('ab', 'xy', 'aabbc')
CRT CONVERT('aa', 'xy', 'aabbc')
CRT CONVERT(@FM:@VM, '^]', 'a':@FM:'b':@VM:'c')
X = 'aabbc' ; CONVERT 'ab' TO 'xy' IN X ; CRT X
