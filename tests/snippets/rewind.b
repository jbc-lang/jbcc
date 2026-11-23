* The guide specifies failure status 1 when the channel has no media.
CRT SYSTEM(0)
REWIND THEN CRT 'unexpected success' ELSE CRT 'default ':SYSTEM(0)
REWIND ON 2 + 3 ELSE CRT 'on ':SYSTEM(0)
REWIND FROM '09' ELSE CRT 'from ':SYSTEM(0)
REWIND UNIT(3)
ELSE
    CRT 'unit ':SYSTEM(0)
END
* The reference generator uses UNIT when both operands are present.
REWIND UNIT(0) ON 1 / 0 ELSE CRT 'unit override ':SYSTEM(0)
REWIND THEN CRT 'unexpected success'
CRT SYSTEM(0):':':STATUS()
REWIND = 'variable'
CRT REWIND
