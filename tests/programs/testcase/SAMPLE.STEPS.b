    SUBROUTINE SAMPLE.STEPS(TRAIL)
* Calls SAMPLE.STEP three times; each answer depends on the mode.
    TRAIL = ''
    FOR I = 1 TO 3
        OUT = ""
        CALL SAMPLE.STEP(I, OUT)
        TRAIL := OUT
    NEXT I
    RETURN
END
