CRT NUM(''):NUM('.'):NUM('+'):NUM('-')
CRT NUM('00012'):NUM('-12.50'):NUM('+12.50'):NUM('.00'):NUM('12.')
CRT NUM('1.2.3'):NUM('1,200'):NUM('1 200'):NUM('12-')
CRT NUM('6.02e23'):NUM('12Q3'):NUM('2+2'):NUM('+.'):NUM(' ')
Value = '003'
IF NUM(Value) THEN CRT NUM(Value + 2)
