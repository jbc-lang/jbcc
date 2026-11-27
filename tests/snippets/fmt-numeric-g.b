* Numeric FMT masks and the G conversion, from the guide's examples.
X = 1234.56
CRT DQUOTE( FMT(X, 'R2#10') ), FMT(X, 'L2%10'), FMT(X, 'R2%10'), FMT(X, 'L2*10'), FMT(X, 'R2*10')
X = 123456.78
CRT DQUOTE( FMT(X, 'R2,$#15') )
CRT DQUOTE( FMT(X, 'R2,&$#15') )
CRT DQUOTE( FMT(X, 'R2,& $#15') )
X = -123456.78
CRT DQUOTE( FMT(X, 'R2,C&*$#15') )
* The other credit indicators, Z, scaling and L justification.
CRT DQUOTE(FMT(-5, 'R2D#8')), DQUOTE(FMT(5, 'R2D#8')), DQUOTE(FMT(-5, 'R2E#8')), DQUOTE(FMT(-5, 'R2M#8')), DQUOTE(FMT(-5, 'R2N#8'))
CRT DQUOTE(FMT(0, 'R2Z#6')), DQUOTE(FMT(123456, 'R22,#10')), DQUOTE(FMT(1234567.5, 'L2,#19'))
the_string = 'LONG STRING TO BE SPLIT'
CRT OCONV(the_string, 'G1 3')
CRT OCONV(the_string, 'G0 1'), OCONV('a/b/c/d', 'G2/5'), '[':OCONV('a b', 'G5 1'):']', FMT('x.y.z', 'G1.1')
* FMT takes OCONV's date and time masks, and OCONV takes FMT's format masks,
* as in the guide's FMT and OCONV examples.
X = 16376
CRT FMT(X, 'D4/'), FMT(X, 'DY'), FMT(X, 'DY2'), FMT(X, 'D2'), FMT(X, 'DQ'), FMT(X, 'DMA'), FMT(X, 'DWA')
CRT FMT(3661, 'MTS'), DQUOTE(OCONV(123456.78, 'R2,$#15')), OCONV(5, 'R2')
