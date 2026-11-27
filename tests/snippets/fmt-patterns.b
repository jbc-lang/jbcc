* FMT pattern masks, with the guide's examples.
X = 1234567890
CRT FMT(X, 'R((###) ###-###)')
CRT FMT(X, 'R((#3) #2-#4)')
CRT FMT(74952223355, 'R(+# (#3) #3-#2-#2)')
date_time = '2203241105'
CRT FMT('20' : date_time, '####-##-##_##:##')
* The guide's UNIQUEKEY example, with a fixed value.
CRT FMT(DOWNCASE(FMT('APWAAADEy5rzj5', 'MX')), 'L(########-####-####-############)')
* Short values: R leaves the leading slots blank, L the trailing ones.
CRT '[':FMT(42, 'R(##-##)'):']', '[':FMT(42, 'L(##-##)'):']', '[':FMT('', 'R(#3)'):']'
CRT FMT('ABC', '#'), FMT('ABC', 'R(#)')
