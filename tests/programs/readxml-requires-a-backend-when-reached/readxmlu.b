* READXML as used by T24 R13 DW.EXPORT.CONF.EXPORT. The guide's READXML
* chapter transforms through the file's DICT @READXML style sheet.
OPEN '', 'F.XML' TO F.XML ELSE NULL
IF 0 THEN READXMLU Skipped FROM F.XML, 'A' ELSE NULL
CRT ASSIGNED(Skipped)
READXMLU Xml FROM F.XML, 'A' LOCKED CRT 'locked' THEN CRT 'read' ELSE CRT 'missing'
CRT 'after'
