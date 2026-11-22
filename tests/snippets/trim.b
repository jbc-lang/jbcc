S = '   A   string  '
PRINT '[' : TRIM(S,' ','L') : ']', '[' : TRIM(S,' ','T') : ']'
PRINT '[' : TRIM(S,' ','B') : ']', '[' : TRIM(S,' ','R') : ']'
PRINT TRIM('000033','0','L'), TRIM(S), TRIM('..A..B..','.')
PRINT TRIM('  A B  ','','A'), LEN(TRIM('    ')), LEN(TRIM(''))
Tab = CHAR(9)
S = Tab : '  A' : Tab : '  B ' : Tab
PRINT '[' : CONVERT(TRIM(S,'','F'),Tab,'~') : ']'
PRINT '[' : CONVERT(TRIM(S,'','E'),Tab,'~') : ']'
Mode = 'D'
PRINT '[' : CONVERT(TRIM(S,'ignored',Mode),Tab,'~') : ']'
PRINT '[' : CONVERT(TRIM(S),Tab,'~') : ']'
PRINT TRIM('A' : @VM : 'B',@VM,'A')
S = '  ' : Tab : ' A  B ' : Tab : '  '
CRT DQUOTE(TRIMF(S))
CRT DQUOTE(TRIMB(S))
CRT DQUOTE(TRIMB(TRIMF('  A  B  ')))
CRT LEN(TRIMF('')), LEN(TRIMB('')), LEN(TRIMF('   ')), LEN(TRIMB('   '))
