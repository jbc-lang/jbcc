    SUBROUTINE SAMPLE.VIA(KEY, VALUE)
* Calls a component method, as R19 code names it in lower case; the test
* stubs the routine that implements it.
    CALL sample.access.fetch(KEY, VALUE)
    RETURN
END
