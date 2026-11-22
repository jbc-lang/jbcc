S = 'a--b----c--'
PRINT COUNT('jjjjj','jjj'), DCOUNT(S,'--'), LEN(FIELD(S,'--',2,2))
PRINT FIELD(S,'--',2,2), FIELD(S,'--',4,9)
PRINT COUNT('',@FM), DCOUNT('',@FM), DCOUNT('A':@FM:'B',@FM)
PRINT NOT('0.00'), NOT('yes')
