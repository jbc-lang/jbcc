* tafc-emulation: prime
* TAFC-CROSSCHECK.md section 5: ICONV date and time forms and STATUS().
FOR I = 1 TO 16
   V = FIELD('20200131,20200231,20201301,31 JAN 2020,31 FEB 2020,31-01-2020,01/31/2020,31/01/2020,2020-01-31,31 JANUARY 2020,JAN 31 2020,31JAN20,abc,,0,1.5', ',', I)
   X = ICONV(V, 'D') ; S = STATUS()
   CRT '[':V:'] D -> [':X:'] ':S
NEXT I
X = ICONV('31/01/2020', 'D4/E') ; CRT 'D4/E -> [':X:'] ':STATUS()
X = ICONV('01/31/2020', 'D4/') ; CRT 'D4/ -> [':X:'] ':STATUS()
FOR I = 1 TO 8
   V = FIELD('12:34,12:34:56,12:99,25:00,1:2,12:34PM,12:34:56 AM,abc', ',', I)
   X = ICONV(V, 'MTS') ; S = STATUS()
   CRT '[':V:'] MTS -> [':X:'] ':S
NEXT I
X = OCONV(19024, 'D') ; CRT 'oconv ok [':X:'] ':STATUS()
X = OCONV('abc', 'D') ; CRT 'oconv text [':X:'] ':STATUS()
X = OCONV('', 'D') ; CRT 'oconv empty [':X:'] ':STATUS()
X = OCONV(99999, 'MTS') ; CRT 'oconv time over [':X:'] ':STATUS()
X = OCONV('abc', 'MTS') ; CRT 'oconv time text [':X:'] ':STATUS()
X = OCONV('abc', 'MD2') ; CRT 'oconv md text [':X:'] ':STATUS()
X = ICONV('12.345', 'MD2') ; CRT 'iconv md [':X:'] ':STATUS()
X = OCONV('abc', 'QWERTY') ; CRT 'bad mask [':X:'] ':STATUS()
