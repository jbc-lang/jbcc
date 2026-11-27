* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 4: & in a numeric mask sets the fill character.
X = 123456.78
CRT DQUOTE(FMT(X, 'R2,$#15'))
CRT DQUOTE(FMT(X, 'R2,&$#15'))
CRT DQUOTE(FMT(X, 'R2,& $#15'))
CRT DQUOTE(FMT(X, 'R2,&*#15'))
CRT DQUOTE(FMT(X, 'R2,&0#15'))
CRT DQUOTE(FMT(-X, 'R2,C&*$#15'))
CRT DQUOTE(FMT(X, 'R2,$*15'))
