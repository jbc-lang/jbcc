* An unattached tape read takes ELSE and sets SYSTEM(0) to one.
* jbcc provisionally assigns an empty string on that path.
Record = 'previous'
READT Record THEN CRT 'unexpected success' ELSE CRT '[':Record:'] ':SYSTEM(0)
READT Fresh FROM 2 + 3
ELSE
    CRT '[':Fresh:'] ':SYSTEM(0)
END
DIM Records(2)
Records(2) = 'previous'
READT UNIT(3) Records(2) ON 1 / 0 ELSE CRT '[':Records(2):'] ':SYSTEM(0)
READT Fresh ON '09' THEN CRT 'unexpected success'
CRT '[':Fresh:'] ':SYSTEM(0):':':STATUS()
READT = 'variable'
CRT READT
