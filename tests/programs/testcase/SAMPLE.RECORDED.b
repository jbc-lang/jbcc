    SUBROUTINE SAMPLE.RECORDED(DAY, NAME, AFTER)
* Reads the date, fetches a name, checks a COMMON flag, then calls a
* routine that stops processing.
    COMMON /SAMPLE.FLAGS/ FLAG
    DAY = OCONV(DATE(), 'D4/E')
    CALL SAMPLE.FETCH(1, NAME)
    CALL SAMPLE.CHECK(FLAG)
    CALL SAMPLE.HALT()
    AFTER = 'reached'
    RETURN
END
