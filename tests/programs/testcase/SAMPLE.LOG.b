    SUBROUTINE SAMPLE.LOG(MESSAGE, RESULT)
* Calls a C function, as T24 routines call Logger through DEFC.
    DEFC INT SampleLog(VAR, INT)
    RESULT = SampleLog(MESSAGE, 3)
    RETURN
END
