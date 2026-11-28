    SUBROUTINE SAMPLE.LOAD(ID, NAME, ERR, COPY)
* Reads records through T24's data-access routines, which a test does not
* stub: the UTF runtime answers them from the test's records. The last is
* a component table read, as R19 code calls Component.Table.Read(id, error).
    FN.SAMPLE = 'F.SAMPLE'
    CALL OPF(FN.SAMPLE, F.SAMPLE)
    CALL F.READ(FN.SAMPLE, ID, REC, F.SAMPLE, ERR)
    NAME = REC<1>
    CALL CACHE.READ('FBNK.SAMPLE', 'MISSING', OTHER, MISSING.ERR)
    IF MISSING.ERR NE '' THEN NAME := '/' : MISSING.ERR
    CALL F.WRITE(FN.SAMPLE, ID : '.COPY', REC)
    DEFFUN sample.records.sample.read(KEY, ERROR)
    COPY = sample.records.sample.read(ID : ".COPY", COPY.ERR)
    RETURN
END
