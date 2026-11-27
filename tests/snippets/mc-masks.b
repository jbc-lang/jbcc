* The MC conversions of the guide's OCONV table, with the guide's examples.
the_string = 'LONG STRING TO BE SPLIT'
the_split = FMT(the_string, '10L')
CRT OCONV(the_split, 'MCP')
CRT OCONV(the_split, 'MCA')
CRT OCONV( OCONV(the_split, 'MC/A'), 'MX' )
CRT OCONV('FB', 'MCXD'), OCONV('251', 'MCDX')
CRT OCONV('another 1 bites the dust', 'MCN')
CRT OCONV('another 1 bites the dust', 'MC/N')
CRT OCONV('a-1 b_2!', 'MCB'), OCONV('a-1 b_2!', 'MC/B')
CRT OCONV(the_string, 'MCC;STRING;DATA')
CRT OCONV(the_string, 'MCL')
CRT OCONV('do it', 'MCU')
CRT OCONV(the_string, 'MCT'), OCONV('mIxEd cASE', 'MCT')
* MCP shows the three marks as ^ ] \ (the guide's note on printing arrays)
* and other non-printable bytes as . or the given character.
V.ARRAY = 1 :@FM: 2 :@VM: 3 :@FM: 4 :@SM: 5 :@TM: 6 : CHAR(7)
CRT FMT(V.ARRAY, 'MCP'), OCONV(V.ARRAY, 'MCP~')
IF OCONV('Do It', 'MCU') = 'DO IT' THEN CRT 'upper'
