X = "jBASE":@VM:"is":@VM:"great":@FM:"!"
Y = REPLACE(X, 1, 2; 'is really')
CRT X
CRT Y
CRT REPLACE(X, 1, 2, 0, 'is really')
CRT REPLACE(X, 2, 0, 0, 'last')
CRT REPLACE('a':@SM:'b':@SM:'c', 1, 1, 2; '')
CRT REPLACE('', 2, 2, 2, 'x')
X = REPLACE(X, -1; 'new')
CRT X<3>
