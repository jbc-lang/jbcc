EQUATE BlockNumber TO 007
COMMON /BlockNumber/ Rows(2)
Rows(2) = 'shared'
COMMON /007/ Rows(2)
COMMON /7/ Other
Other = 'separate'
CRT Rows(2), Other
