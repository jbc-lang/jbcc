* @COMPANYNO as T24 R19 sets it: LOAD.COMPANY clears it and
* EB.QUERY.BUILDER stores the company position from the company record.
CRT '[':@COMPANYNO:']'
@COMPANYNO = 3
CRT @COMPANYNO + 1
GOSUB Reset
CRT '[':@COMPANYNO:']'
STOP
Reset:
   @COMPANYNO = ''
RETURN
