* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 6: TRANS and XLATE codes.
* jbcc-options: --memory-file VENDORS
EXECUTE 'CREATE-FILE VENDORS 1 1' CAPTURING JUNK
OPEN 'VENDORS' TO F ELSE STOP 201, 'VENDORS'
WRITE 'ABC Company':@FM:'x':@VM:'y':@SM:'z':@FM:'' TO F, '12345'
CRT '1 [':TRANS('VENDORS', '12345', 1, 'X'):']'
CRT '2 [':OCONV(TRANS('VENDORS', '12345', 2, 'X'), 'MX'):']'
CRT '3 [':OCONV(TRANS('VENDORS', '12345', -1, 'X'), 'MX'):']'
CRT '4 [':TRANS('VENDORS', 'NOPE', 1, 'X'):']'
CRT '5 [':TRANS('VENDORS', 'NOPE', 1, 'C'):']'
CRT '6 [':TRANS('VENDORS', '12345', 3, 'C'):']'
CRT '7 [':TRANS('VENDORS', 'NOPE', 1, 'V'):'] ':STATUS()
CRT '8 [':XLATE('VENDORS', '12345', 1, 'X'):']'
CRT '9 [':OCONV(TRANS('VENDORS', '12345':@VM:'NOPE', 1, 'X'), 'MCP'):']'
