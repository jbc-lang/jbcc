Info = 'old'
CRT CALLC JBASESubroutineExist('WOR':'KER', Info), '[':Info:']'
CRT CALLC JBASESubroutineExist('worker', 0), CALLC JBASESubroutineExist('COMPUTE', Info)
Name = 'WORKER'
CRT CALLC JBASESubroutineExist(Name, Name), '[':Name:']'
DIM Codes(1)
CALLC JBASESubroutineExist('missing', Codes(1))
CRT '[':Codes(1):']'
