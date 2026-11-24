Marks = @FM:@VM:@SM
Values = '-0.5':@VM:'x':@SM:'':@FM:'1,000':@VM:'.25':@FM
CRT CONVERT(NUMS(Values), Marks, '|:/')
CRT NUMS(''), NUMS('7'), NUMS('$1'), NUMS('1e3')
