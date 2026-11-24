# API coverage

This snapshot covers expression calls and the direct `DEFC` declarations
in the documentation repo's catalogues. The full JSON includes guide
links, arities, recognized forms, occurrence and translation-unit
counts, and example source locations. See the [scan command](README.md#api-coverage)
to reproduce it.

The corpus scan passed strict C99 checking for 17,336 units.

| Catalogue | Entries | Recognized in T24 | No recognized call in T24 |
|---|---:|---:|---:|
| Expression calls | 210 | 122 | 88 |
| `JBC.h` declarations | 53 | 15 | 38 |

Reviewed runtime assertions are linked for 17 APIs. Repo snippets
reference 99 APIs and are indexed in JSON.

## Runtime evidence by form

| API | Form | Guide | T24 units | jbcc support | Runtime evidence |
|---|---|---|---:|---|---|
| `CacheBucketList` | 1 argument | [Guide](https://jbc-lang.org/pages/cachebucketlist.html) | 2 | backend required | Unreviewed |
| `CacheClear` | 1 argument | [Guide](https://jbc-lang.org/pages/cacheclear.html) | 1 | backend required | Unreviewed |
| `CacheDelete` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachedelete.html) | 1 | backend required | Unreviewed |
| `CacheExists` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheexists.html) | 2 | backend required | Unreviewed |
| `CacheGet` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheget.html) | 2 | backend required | Unreviewed |
| `CachePut` | 3 arguments | [Guide](https://jbc-lang.org/pages/cacheput.html) | 4 | backend required | Unreviewed |
| `CacheStats` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachestats.html) | 2 | backend required | Unreviewed |
| `JBASEGetInode` | 1 argument | — | 1 | backend required | Unreviewed |
| `JBASEGetPidFromPort` | 1 argument | — | 2 | backend required | Unreviewed |
| `JEEActivate` | 3 arguments | — | 1 | backend required | Unreviewed |
| `JEEOpen` | 2 arguments | — | 1 | backend required | Unreviewed |
| `JIMITraceOff` | 1 argument | — | 2 | backend required | Unreviewed |
| `JIMITraceOn` | 3 arguments | — | 2 | backend required | Unreviewed |
| `Logger` | 3 arguments | [Guide](https://jbc-lang.org/pages/logger.html) | 2 | backend required | Unreviewed |
| `LoggerDescribe` | 2 arguments | — | 3 | backend required | Unreviewed |
| `MONEndUnitOfWork` | 0 arguments | — | 4 | backend required | Unreviewed |
| `MONStartUnitOfWork` | 1 argument | — | 4 | backend required | Unreviewed |
| `BITOR` | 2 arguments | [Guide](https://jbc-lang.org/pages/bitor.html) | 1 | call translates | [Signed 32-bit output checked](tests/snippets/bitor.b) |
| `DATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/date.html) | 602 | call translates | [Local date and epoch checked](tests/test_terminal.py) |
| `DECRYPT` | computed method | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | runtime support depends on method | Unreviewed |
| `DECRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `DECRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 10 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `DECRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | backend required | Unreviewed |
| `DYNTOXML` | 2 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `DYNTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `ENCRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `ENCRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 8 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `ENCRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/encrypt.html) | 1 | backend required | Unreviewed |
| `FILEINFO` | 2 arguments | [Guide](https://jbc-lang.org/pages/fileinfo.html) | 8 | call translates | [Handle status and pathname checked](tests/test_io.py) |
| `GETENV` | 1 argument | [Guide](https://jbc-lang.org/pages/getenv.html) | 2 | call translates | [Environment lookup checked](tests/io/getenv.b) |
| `GETENV` | 2 arguments | [Guide](https://jbc-lang.org/pages/getenv.html) | 16 | call translates | [Environment lookup and output parameter checked](tests/io/getenv.b) |
| `INDICES` | 1 argument | — | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INDICES` | 2 arguments | — | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INMAT` | 0 arguments | [Guide](https://jbc-lang.org/pages/inmat.html) | 8 | call translates | [Latest matrix load count checked](tests/io/inmat.b) |
| `INMAT` | 1 argument | [Guide](https://jbc-lang.org/pages/inmat.html) | 3 | call translates | [Matrix bounds checked](tests/io/inmat.b) |
| `IOCTL` | 3 arguments | [Guide](https://jbc-lang.org/pages/ioctl.html) | 5 | call translates | [Filename query and output parameter checked](tests/test_io.py) |
| `ITYPE` | 1 argument | [Guide](https://jbc-lang.org/pages/itype.html) | 8 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `JBASECOREDUMP` | 2 arguments | [Guide](https://jbc-lang.org/pages/jbasecoredump.html) | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `PUTENV` | 1 argument | [Guide](https://jbc-lang.org/pages/putenv.html) | 7 | call translates | [Environment updates checked](tests/io/putenv.b) |
| `TIME` | 0 arguments | [Guide](https://jbc-lang.org/pages/time.html) | 344 | call translates | [Local clock checked](tests/test_terminal.py) |
| `TIMEDATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/timedate.html) | 587 | call translates | [Local midnight rollover checked](tests/test_terminal.py) |
| `XMLTODYN` | 2 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTODYN` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltoxml.html) | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |

## Frequent T24 forms without a linked test

The JSON contains 31 observed forms with neither a reviewed runtime
assertion nor a snippet reference. The table shows up to ten forms,
ordered by the number of translation units.

| API | Form | T24 units |
|---|---|---:|
| `CachePut` | 3 arguments | 4 |
| `MONEndUnitOfWork` | 0 arguments | 4 |
| `MONStartUnitOfWork` | 1 argument | 4 |
| `LoggerDescribe` | 2 arguments | 3 |
| `ASCII` | 1 argument | 3 |
| `CacheBucketList` | 1 argument | 2 |
| `CacheExists` | 2 arguments | 2 |
| `CacheGet` | 2 arguments | 2 |
| `CacheStats` | 2 arguments | 2 |
| `JBASEGetPidFromPort` | 1 argument | 2 |

## Catalogue entries by corpus observation

### Expression calls recognized in T24

`@`, `ABS`, `ABSS`, `ADDS`, `ALPHA`, `ASCII`, `ASSIGNED`, `BITOR`, `BITXOR`, `BYTELEN`,
`CALLC`, `CALLONEXIT`, `CATS`, `CHANGE`, `CHAR`, `CHECKSUM`, `COL2`, `COMPARE`,
`CONVERT`, `COUNT`, `COUNTS`, `DATE`, `DCOUNT`, `DECRYPT`, `DELETE`, `DIV`, `DIVS`,
`DOWNCASE`, `DQUOTE`, `DROUND`, `DTX`, `DYNTOXML`, `EBCDIC`, `ENCRYPT`, `EQS`,
`EREPLACE`, `EXP`, `EXTRACT`, `FIELD`, `FIELDS`, `FILEINFO`, `FMT`, `FMTS`, `FOLD`,
`GETENV`, `GROUP`, `GTS`, `ICONV`, `ICONVS`, `INDEX`, `INDICES`, `INMAT`, `INSERT`,
`INT`, `IOCTL`, `ISALPHA`, `ISDIGIT`, `ITYPE`, `JBASECOREDUMP`, `JBASESubroutineExist`,
`KEYIN`, `LEFT`, `LEN`, `LENDP`, `LES`, `LN`, `LOWCASE`, `LOWER`, `MATCHFIELD`,
`MAXIMUM`, `MINIMUM`, `MOD`, `MULS`, `NEG`, `NEGS`, `NES`, `NOT`, `NUM`, `OCONV`,
`OCONVS`, `PUTENV`, `PWR`, `QUOTE`, `RAISE`, `RECORDLOCKED`, `REM`, `REMOVE`, `REPLACE`,
`REUSE`, `RIGHT`, `RND`, `SDIV`, `SENTENCE`, `SEQ`, `SMUL`, `SORT`, `SPACE`, `SPACES`,
`SPLICE`, `SQRT`, `SQUOTE`, `STATUS`, `STR`, `SUBS`, `SUBSTRINGS`, `SUM`, `SUMMATION`,
`SWAP`, `SYSTEM`, `TIME`, `TIMEDATE`, `TRIM`, `TRIMB`, `TRIMBS`, `TRIMF`, `TRIMS`,
`UNASSIGNED`, `UPCASE`, `UTF8`, `XMLTODYN`, `XMLTOXML`, `XTD`

### Expression calls with no recognized call in T24

`ACOS`, `ANDS`, `ASIN`, `ATAN`, `BITAND`, `BITCHANGE`, `BITCHECK`, `BITLOAD`, `BITNOT`,
`BITRESET`, `BITSET`, `BITTEST`, `CHANGETIMESTAMP`, `CHARS`, `CHDIR`, `COL1`,
`CONSUME_METRICS_LICENSE`, `CONTROLCHAR`, `COS`, `CRC`, `DELENV`, `DIR`, `ERRTEXT`,
`FADD`, `FCMP`, `FDIV`, `FFIX`, `FFLT`, `FMUL`, `FSUB`, `GES`, `GETCWD`, `GETUSERGROUP`,
`GETUSERNAME`, `IFS`, `IN`, `ISALNUM`, `ISCNTRL`, `ISGRAPH`, `ISLOWER`, `ISPRINT`,
`ISPUNCT`, `ISSPACE`, `ISUPPER`, `ISXDIGIT`, `JQLCOMPILE`, `JQLEXECUTE`, `JQLFETCH`,
`JQLGETPROPERTY`, `JQLPUTPROPERTY`, `LATIN1`, `LENS`, `LENSDP`, `LOCALDATE`,
`LOCALTIME`, `LTS`, `MAKETIMESTAMP`, `MODS`, `NOTS`, `NUMS`, `ORS`, `PERROR`, `REGEXP`,
`SADD`, `SCMP`, `SELECTINFO`, `SEQS`, `SIN`, `SOUNDEX`, `SPOOLER`, `SSUB`, `STRS`, `TA`,
`TAN`, `TIMEDIFF`, `TIMESTAMP`, `TRANS`, `TRANSQUERY`, `TRANSSYNC`, `TRIMFS`,
`UNIQUEKEY`, `VALIDATE_METRICS_LICENSE`, `VALIDATE_PRODUCT_LICENSE`, `XLATE`,
`XML.ADD.NODE`, `XML.ADD.TEXT`, `XML.GET.TAG.VALUE`, `XML.VALIDATE`

### JBC.h declarations recognized in T24

`CacheBucketList`, `CacheClear`, `CacheDelete`, `CacheExists`, `CacheGet`, `CachePut`,
`CacheStats`, `JBASEGetInode`, `JBASEGetPidFromPort`, `JEEActivate`, `JEEOpen`,
`Logger`, `LoggerDescribe`, `MONEndUnitOfWork`, `MONStartUnitOfWork`

### JBC.h declarations with no recognized call in T24

`BuildFileList`, `CALLJEE`, `CacheClearAll`, `CacheClearStats`, `CacheGetOption`,
`CacheKeyList`, `CacheSetOption`, `GetProperty`, `JBASEAccess`, `JBASEAssertEquals`,
`JBASEAssertTrue`, `JBASECALLC`, `JBASECanonicalInput`, `JBASECheckRemote`,
`JBASEGetDevInode`, `JBASEGetPortFromPid`, `JBASEReturnLockInfo`, `JBASEScanfileEnd`,
`JBASEScanfileInit`, `JBASEScanfileRead`, `JBASETHREADCreate`, `JBASETHREADStatus`,
`JBASEThreadGetRootStatus`, `JBASEThreadSendMessage`, `JBASEThreadSetRootStatus`,
`JBASEUserProfile`, `JEEClose`, `JEEOpenSSL`, `LoggerDebugPrint`, `LoggerPrint`,
`LoggerVerbosePrint`, `MONAddRepetitiveUnitOfWork`, `MONAddSingleUnitOfWork`,
`MONCurrentUnitOfWork`, `MONDump`, `MONIsInsideUnitOfWork`, `MONIsUnitOfWorkMonitored`,
`PutProperty`

### Recognized calls outside the catalogues

`JIMITraceOff` (defc), `JIMITraceOn` (defc)

Counts reflect calls recognized by jbcc after include and equate expansion.
A call in a shared include can contribute to several units. A zero count
means this scan found no recognized call. Rejected units can contribute
observations up to the first compiler diagnostic. The scan covers
expression calls and declared external C calls. Statically referenced
snippets are recorded in JSON as leads for test review. The runtime table
links to reviewed assertions. Other runtime evidence is unreviewed.
