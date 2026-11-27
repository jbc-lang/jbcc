* TAN takes degrees like SIN and COS. The guide documents TAN only; ASIN,
* ACOS and ATAN return degrees by the same convention (provisional).
CRT TAN(0):' ':TAN(45):' ':TAN(-45)
CRT ASIN(1):' ':ASIN(-0.5):' ':ACOS(0):' ':ACOS(1):' ':ATAN(1):' ':ATAN(0)
* Guide TAN example: Opposite length = TAN(Angle) * Adjacent.
PRECISION 4
CRT "Opposite length = " : TAN(34)*42
