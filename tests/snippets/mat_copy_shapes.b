N = 2
DIM Grid(N,2), Vector(5), Short(2)
COMMON Other(1,3)
MAT Grid = 'padding'
Grid(0,0) = 'zero'
Grid(1,1) = 'a'
Grid(1,2) = 'b'
Grid(2,1) = 'c'
Grid(2,2) = 'd'
MAT Vector = 'tail'
MAT Vector = MAT Grid
PRINT Vector(0), Vector(1), Vector(2), Vector(3), Vector(4), Vector(5)
MAT Short = MAT Vector
PRINT Short(0), Short(1), Short(2)
MAT Other = 'padding'
MAT Other = MAT Grid
PRINT Other(0,0), Other(0,1), Other(1,1), Other(1,2), Other(1,3)
MAT Grid = 'keep'
MAT Grid = MAT Short
PRINT Grid(0,0), Grid(0,1), Grid(1,1), Grid(1,2), Grid(2,1)
MAT Short = 'new'
MAT Vector = MAT Short
PRINT Vector(0), Vector(1), Vector(2), Vector(3), Vector(4), Vector(5)
