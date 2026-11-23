* The guide specifies status 1 for an unattached tape channel.
Record = 'payload'
WRITET Record THEN CRT 'unexpected success' ELSE CRT SYSTEM(0):' ':Record
WRITET Record:'!' ON 1 + 2 ELSE CRT 'on ':SYSTEM(0)
WRITET 'data' TO 9
ELSE
    CRT 'to ':SYSTEM(0)
END
WRITET 'data' FROM 5 ELSE CRT 'from ':SYSTEM(0)
WRITET UNIT(3) 'data' ON 1 / 0 ELSE CRT 'unit ':SYSTEM(0)
WRITET 'data' THEN CRT 'unexpected success'
CRT SYSTEM(0):':':STATUS()
WRITET = 'variable'
CRT WRITET
