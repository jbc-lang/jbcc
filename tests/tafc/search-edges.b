* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: INDEX, COUNT, DCOUNT and EREPLACE edges.
CRT INDEX('aaa', 'aa', 2), INDEX('abc', '', 1), INDEX('abc', '', 2), INDEX('', '', 1), INDEX('abab', 'ab', 2.7)
CRT COUNT('aaa', 'aa'), COUNT('abc', ''), DCOUNT('aaa', 'aa'), DCOUNT('', ','), DCOUNT('a', ',')
CRT '[':EREPLACE('AAB', '', 'Z'):'] [':EREPLACE('', '', 'Z'):']'
CRT EREPLACE('AAA', 'A', 'B', 2), ' ', EREPLACE('AAA', 'A', 'B', 2, 2), ' ', EREPLACE('AAA', 'A', 'B', 0, 2)
