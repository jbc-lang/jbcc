Value = 'a::b::c::'
CRT GROUP(Value, '::', 2), COL1(), COL2()
CRT GROUP(Value, '::', 2, 2), COL1(), COL2()
CRT '[':GROUP(Value, '::', 4):']', COL1(), COL2()
CRT '[':GROUP(Value, '::', 5):']', COL1(), COL2()
CRT GROUP('plain', '', 1), COL1(), COL2()
CRT GROUP('a::b::c', '::', 2, 20)
