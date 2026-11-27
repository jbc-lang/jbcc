* As in T24 R19 EB.API ConvertLocaleDateToGregorian.
IF 0 THEN CRT DATEGREGORIANTOLOCALE('x', 'yyyyMMdd', 'islamic', 'yyyyMMdd', 'en_US')
CRT 'start'
Converted = DATEGREGORIANTOLOCALE ('14450101', "yyyyMMdd", 'islamic', "yyyyMMdd", "en_US")
CRT Converted
