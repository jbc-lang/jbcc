CRT LEN(SPACES(255)), LEN(SPACES(0)), LEN(SPACES(-3)), LEN(SPACES(2.75))
Counts = 2:@FM:0:@VM:3:@SM:1:@FM:0
Result = SPACES(Counts)
CRT CONVERT(' ':@FM:@VM:@SM, '._|/', Result)
CRT Counts = 2:@FM:0:@VM:3:@SM:1:@FM:0
CRT SPACES(5) = SPACE(5)
