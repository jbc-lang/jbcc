COMMON /STATE/ Shared, Cache(2)
COMMON Unnamed
Shared = 10
Unnamed = 11
Cache(1) = 12
DIM Buffer(2)
Buffer(0) = 13
Value = 14
CALL RESET(Value, MAT Buffer, 0)
CALL RESET(Value, MAT Buffer, 1)
CRT Shared:':':Unnamed:':':Cache(1):':':Buffer(0):':':Value
