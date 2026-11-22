Config<1> = 2
DIMENSION Line(Config<1>), Grid(Config<1>, Config<1> + 1)
Config<1> = 1
MAT Grid = 'cell'
Line(2) = 'edge'
Grid(2,3) = Line(2)
CRT Grid(0,0):' ':Grid(2,3)
FOR I = 1 TO 2
    DIM Saved(Config<1>)
    IF I = 1 THEN Saved(1) = 'kept'
NEXT I
CRT Saved(1)
