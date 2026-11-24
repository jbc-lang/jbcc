DIM Codes(1)
IF 0 THEN CRT DYNTOXML('skip', '', Skipped)
CRT ASSIGNED(Skipped)
Value = XMLTOXML('<doc/>', '', Code)
CRT Code
