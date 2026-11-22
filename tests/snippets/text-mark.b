CRT @TM EQ CHAR(251)
Line = "one" : @TM : "two"
Record = Line : @SM : "three"
CRT FIELD(Record<1,1,1>, @TM, 2)
CHANGE @TM TO "/" IN Line
CRT Line
CRT @SVM EQ CHAR(252)
CRT @IM EQ CHAR(255)
CRT @RM EQ @IM
