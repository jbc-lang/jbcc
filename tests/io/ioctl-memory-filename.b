OPEN 'customers' TO F ELSE ABORT
OPEN 'customers' ELSE ABORT
IF IOCTL(F, 100, Name) AND Name = 'customers' THEN CRT Name, FILEINFO(Name, 0) ELSE ABORT
Name = 'old'
CRT Name:':':IOCTL(-1, 100, Name):':':Name
DIM Names(1)
IF IOCTL(F, 100, Names(1)) THEN CRT Names(1) ELSE ABORT
CRT IOCTL(F, 100, '')
CLOSE F
IF IOCTL(F, 100, Name) THEN ABORT ELSE CRT Name
CRT IOCTL('customers', 100, Name)
