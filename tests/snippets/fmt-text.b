* Text masks prefer word breaks and pad blocks to the requested width.
CRT '[':CONVERT(@TM, '|', FMT('one two three', '7T')):']'
CRT '[':CONVERT(@TM, '|', FMT('  aa bbbb cc ', "5'.'T")):']'
CRT '[':CONVERT(@TM, '|', FMT('longword z', '4T')):']'
CRT '[':FMT('', '4T'):'][':FMT('  ', '4T'):']'
Width = 6
Narrative = ' send  funds ':@VM:'ready now'
CRT '[':CONVERT(@VM:@TM, '/|', FMTS(TRIMS(Narrative), Width:'T')):']'
