GOSUB Initialize
CALL CHECK(MAT Rows, MAT Flags, MAT Shared)
CRT Rows(2,1):':':Flags(1):':':Shared(2)
STOP
Initialize:
Config<1,1> = 2
$INSERT I_ARRAYS
Rows(2,1) = 'rows'
Flags(1) = 'flags'
Shared(2) = 'common'
RETURN
