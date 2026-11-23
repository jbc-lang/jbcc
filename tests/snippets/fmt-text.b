* Text masks prefer word breaks and pad blocks to the requested width.
CRT '[':CONVERT(FMT('one two three', '7T'), @TM, '|'):']'
CRT '[':CONVERT(FMT('  aa bbbb cc ', "5'.'T"), @TM, '|'):']'
CRT '[':CONVERT(FMT('longword z', '4T'), @TM, '|'):']'
CRT '[':FMT('', '4T'):'][':FMT('  ', '4T'):']'
Width = 6
Narrative = ' send  funds ':@VM:'ready now'
CRT '[':CONVERT(FMTS(TRIMS(Narrative), Width:'T'), @VM:@TM, '/|'):']'
