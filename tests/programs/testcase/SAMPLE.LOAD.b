    SUBROUTINE SAMPLE.LOAD(ID, NAME, ERR, COPY)
* Reads records through T24's data-access routines, which a test does not
* stub: the UTF runtime answers them from the test's records. The last is
* a component table read, as R19 code calls Component.Table.Read(id, error).
    FN.SAMPLE = 'F.SAMPLE'
    CALL OPF(FN.SAMPLE, F.SAMPLE)
* The target's own statements see the same records: READ through the OPF
* handle, and OPEN of the file under its company name.
    READ VIA.OPF FROM F.SAMPLE, ID ELSE VIA.OPF = 'none'
    OPEN 'FBNK.SAMPLE' TO F.OPENED ELSE RETURN
    WRITE VIA.OPF<2> ON F.OPENED, 'STATEMENT'
    CALL F.READ(FN.SAMPLE, ID, REC, F.SAMPLE, ERR)
    NAME = REC<1>
    CALL CACHE.READ('FBNK.SAMPLE', 'MISSING', OTHER, MISSING.ERR)
    IF MISSING.ERR NE '' THEN NAME := '/' : MISSING.ERR
    CALL F.WRITE(FN.SAMPLE, ID : '.COPY', REC)
    DEFFUN sample.records.sample.read(KEY, ERROR)
    COPY = sample.records.sample.read(ID : ".COPY", COPY.ERR)
* A component's table<Name> read, and F.RELEASE, which releases a lock.
    DEFFUN sample.records.tablesample(KEY, ERROR)
    COPY<3> = sample.records.tablesample(ID, TABLE.ERR)<1>
    CALL F.RELEASE(FN.SAMPLE, ID, F.SAMPLE)
    RETURN
END
