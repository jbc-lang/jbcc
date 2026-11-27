* The MCP mask, from the guide's note on printing dynamic arrays: it shows
* field, value and subvalue marks as ^, ] and \.
V.ARRAY = 1 :@FM: 2 :@VM: 3 :@FM: 4 :@SM: 5
CRT FMT(V.ARRAY, 'MCP')
CRT OCONV(V.ARRAY, 'MCP')
dyn_array = 'qwe' : @FM : "rty" : @VM : 'xYZ'
CRT FMT(UPCASE(dyn_array), 'MCP')
CRT '[' : OCONV('', 'MCP') : ']', OCONV('plain text', 'MCP')
