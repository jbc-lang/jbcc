FOR Outer = 1 TO 2
    FOR Inner = 1 TO 3 STEP 2
        CRT Outer : '.' : Inner
    NEXT Outer
    CRT 'inner ' : Inner
NEXT Unused
CRT 'outer ' : Outer
