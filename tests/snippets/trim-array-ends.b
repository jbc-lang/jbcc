Tab = CHAR(9)
Text = @FM:Tab:'  a  b ':Tab:@VM:' ':Tab:@SM:' x ':@FM
CRT TRIMBS(Text)
CRT TRIMFS(Text)
CRT '[':TRIMBS(''):'] [':TRIMFS(''):']'
CRT '[':TRIMS(Tab:'  q  ':Tab):']'
