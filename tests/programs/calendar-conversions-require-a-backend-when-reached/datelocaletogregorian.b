* As in T24 R19 EB.API ConvertLocaleDateToGregorian.
IF 0 THEN CRT DATELOCALETOGREGORIAN('x', 'yyyyMMdd', 'islamic', 'yyyyMMdd', 'en_US')
CRT 'start'
Converted = DATELOCALETOGREGORIAN ('14450101', "yyyyMMdd", 'islamic', "yyyyMMdd", "en_US")
CRT Converted
