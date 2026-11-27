* The first two products come from the jBASE SMUL guide. The guide prints
* 0.0000000000001714 for the second; TAFC PB201214 truncates to 14 places.
CRT SMUL(243603310027840922, 3760)
CRT SMUL(0.0000000000000475, 3.61)
* The explicit fractional limit and -1 default follow provisional jbcc rules.
CRT SMUL('0.0000000000000475', '3.61', 18)
CRT SMUL('0.0000000000000475', '3.61', -1)
CRT SMUL('99999999999999999999', 9)
CRT SMUL('-001.25', '+2.4', 1000000000)
CRT SMUL('-1.259', 2, 2)
CRT SMUL('-0.001', 2, 2)
CRT SMUL('-1.259', 2, 0)
CRT SMUL(0, '-1.25')
PRECISION 1
CRT SMUL('0.125', '0.125')
