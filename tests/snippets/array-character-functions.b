* Guide SEQS example.
G = 'T' :@VM: "G"
A = SEQS(G)
PRINT OCONV(A, 'MCP')
PRINT SEQS('G')
CRT OCONV(SEQS('a' :@VM: '' :@SM: 'bc'), 'MCP')
* Guide CHARS example displays ;-)
V.ARRAY = 59 :@FM: 45 :@FM: 41
V.CHARS = CHARS(V.ARRAY)
CRT CHANGE(V.CHARS, @FM, '')
CRT OCONV(CHARS(65 :@VM: '' :@VM: 66), 'MCP')
* Guide STRS example.
ABC= "A" :@VM: "B" :@VM: "C"
PRINT OCONV(STRS(ABC,3), 'MCP')
CRT OCONV(STRS('ab' :@SM: '' :@SM: 'c', 2), 'MCP'):'[':STRS(ABC, 0):']'
* LENSDP counts bytes like LENS in the byte runtime.
CRT OCONV(LENSDP('abc' :@VM: '' :@VM: 'de'), 'MCP')
