* The guide specifies status 1 for an unattached tape channel.
WEOF ELSE CRT 'default ':SYSTEM(0)
WEOF ON 9 THEN CRT 'unexpected success' ELSE CRT 'on ':SYSTEM(0)
WEOF FROM 2 + 3
ELSE
    CRT 'from ':SYSTEM(0)
END
WEOF UNIT(3) ON 1 / 0 ELSE CRT 'unit ':SYSTEM(0)
WEOF THEN CRT 'unexpected success'
CRT SYSTEM(0):':':STATUS()
WEOF = 'variable'
CRT WEOF
