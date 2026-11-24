PROMPT ''
CLEARDATA
DATA 'first':@FM:'discard this', 'discard this too'
INPUT First
IF First = 'first' THEN CLEARDATA
INPUT FromPipe
DATA 'fresh'
INPUT FromData
CLEARDATA = 'variable'
CRT First:':':FromPipe:':':FromData:':':CLEARDATA
