# API coverage

This snapshot covers expression calls and the direct `DEFC` declarations
in the documentation repo's catalogues. The full JSON includes guide
links, arities, recognized forms, occurrence and translation-unit
counts, and example source locations. See the [scan command](README.md#api-coverage)
to reproduce it.

The `201307-R13` corpus scan passed strict C99 checking for 19,536 units.

| Catalogue | Entries | Recognized in T24 | No recognized call in T24 |
|---|---:|---:|---:|
| Expression calls | 210 | 129 | 81 |
| `JBC.h` declarations | 53 | 18 | 35 |

Reviewed runtime assertions are linked for 22 APIs. Repo snippets
reference 103 APIs and are indexed in JSON.

## Runtime evidence by form

| API | Form | Guide | T24 units | jbcc support | Runtime evidence |
|---|---|---|---:|---|---|
| `CALLJEE` | 2 arguments | [Guide](https://jbc-lang.org/pages/calljee.html) | 1 | backend required | Unreviewed |
| `CacheBucketList` | 1 argument | [Guide](https://jbc-lang.org/pages/cachebucketlist.html) | 3 | backend required | Unreviewed |
| `CacheClear` | 1 argument | [Guide](https://jbc-lang.org/pages/cacheclear.html) | 1 | backend required | Unreviewed |
| `CacheDelete` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachedelete.html) | 1 | backend required | Unreviewed |
| `CacheExists` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheexists.html) | 5 | backend required | Unreviewed |
| `CacheGet` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheget.html) | 4 | backend required | Unreviewed |
| `CachePut` | 3 arguments | [Guide](https://jbc-lang.org/pages/cacheput.html) | 5 | backend required | Unreviewed |
| `CacheStats` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachestats.html) | 3 | backend required | Unreviewed |
| `GetProperty` | 2 arguments | — | 2 | backend required | Unreviewed |
| `JBASEGetInode` | 1 argument | — | 1 | backend required | Unreviewed |
| `JBASEGetPidFromPort` | 1 argument | — | 6 | backend required | Unreviewed |
| `JBASE_utf8_convert_var_codepage_to_utf8_BBB` | 2 arguments | — | 2 | backend required | Unreviewed |
| `JBASE_utf8_setpage_IIS` | 2 arguments | — | 1 | backend required | Unreviewed |
| `JEEActivate` | 3 arguments | — | 1 | backend required | Unreviewed |
| `JEEOpen` | 2 arguments | — | 1 | backend required | Unreviewed |
| `JIMITraceOff` | 1 argument | — | 2 | backend required | Unreviewed |
| `JIMITraceOn` | 3 arguments | — | 2 | backend required | Unreviewed |
| `Logger` | 3 arguments | [Guide](https://jbc-lang.org/pages/logger.html) | 34 | backend required | Unreviewed |
| `LoggerDescribe` | 2 arguments | — | 1 | backend required | Unreviewed |
| `LoggerPrint` | 3 arguments | — | 1 | backend required | Unreviewed |
| `MONEndUnitOfWork` | 0 arguments | — | 4 | backend required | Unreviewed |
| `MONStartUnitOfWork` | 1 argument | — | 4 | backend required | Unreviewed |
| `BITAND` | 2 arguments | [Guide](https://jbc-lang.org/pages/bitand.html) | 1 | call translates | [Signed 32-bit output checked](tests/snippets/bitand.b) |
| `BITNOT` | 1 argument | [Guide](https://jbc-lang.org/pages/bitnot.html) | 1 | call translates | [Unsigned 32-bit output checked](tests/snippets/bitand.b) |
| `BITOR` | 2 arguments | [Guide](https://jbc-lang.org/pages/bitor.html) | 3 | call translates | [Signed 32-bit output checked](tests/snippets/bitor.b) |
| `CHDIR` | 1 argument | [Guide](https://jbc-lang.org/pages/chdir.html) | 1 | call translates | [Directory change and failure checked](tests/io/chdir.b) |
| `DATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/date.html) | 669 | call translates | [Local date and epoch checked](tests/test_terminal.py) |
| `DECRYPT` | computed method | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | runtime support depends on method | Unreviewed |
| `DECRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `DECRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 10 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `DECRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | backend required | Unreviewed |
| `DYNTOXML` | 2 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `DYNTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 3 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `ENCRYPT` | computed method | [Guide](https://jbc-lang.org/pages/encrypt.html) | 1 | runtime support depends on method | Unreviewed |
| `ENCRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `ENCRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 8 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `ENCRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/encrypt.html) | 1 | backend required | Unreviewed |
| `FILEINFO` | 2 arguments | [Guide](https://jbc-lang.org/pages/fileinfo.html) | 15 | call translates | [Handle status and pathname checked](tests/test_io.py) |
| `GETENV` | 1 argument | [Guide](https://jbc-lang.org/pages/getenv.html) | 3 | call translates | [Environment lookup checked](tests/io/getenv.b) |
| `GETENV` | 2 arguments | [Guide](https://jbc-lang.org/pages/getenv.html) | 27 | call translates | [Environment lookup and output parameter checked](tests/io/getenv.b) |
| `INDICES` | 1 argument | — | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INDICES` | 2 arguments | — | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INMAT` | 0 arguments | [Guide](https://jbc-lang.org/pages/inmat.html) | 12 | call translates | [Latest matrix load count checked](tests/io/inmat.b) |
| `INMAT` | 1 argument | [Guide](https://jbc-lang.org/pages/inmat.html) | 3 | call translates | [Matrix bounds checked](tests/io/inmat.b) |
| `IOCTL` | 3 arguments | [Guide](https://jbc-lang.org/pages/ioctl.html) | 7 | call translates | [Filename query and output parameter checked](tests/test_io.py) |
| `ISALNUM` | 1 argument | [Guide](https://jbc-lang.org/pages/isalnum.html) | 1 | call translates | [ASCII letters and digits checked](tests/snippets/character-class-predicates.b) |
| `ITYPE` | 1 argument | [Guide](https://jbc-lang.org/pages/itype.html) | 7 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `JBASECOREDUMP` | 2 arguments | [Guide](https://jbc-lang.org/pages/jbasecoredump.html) | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `PUTENV` | 1 argument | [Guide](https://jbc-lang.org/pages/putenv.html) | 13 | call translates | [Environment updates checked](tests/io/putenv.b) |
| `TIME` | 0 arguments | [Guide](https://jbc-lang.org/pages/time.html) | 385 | call translates | [Local clock checked](tests/test_terminal.py) |
| `TIMEDATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/timedate.html) | 625 | call translates | [Local midnight rollover checked](tests/test_terminal.py) |
| `VALIDATE_PRODUCT_LICENSE` | 1 argument | — | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTODYN` | 2 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTODYN` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltoxml.html) | 3 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |

## Frequent T24 forms without a linked test

The JSON contains 39 observed forms with neither a reviewed runtime
assertion nor a snippet reference. The table shows up to ten forms,
ordered by the number of translation units.

| API | Form | T24 units |
|---|---|---:|
| `Logger` | 3 arguments | 34 |
| `JBASEGetPidFromPort` | 1 argument | 6 |
| `CacheExists` | 2 arguments | 5 |
| `CachePut` | 3 arguments | 5 |
| `CacheGet` | 2 arguments | 4 |
| `MONEndUnitOfWork` | 0 arguments | 4 |
| `MONStartUnitOfWork` | 1 argument | 4 |
| `ASCII` | 1 argument | 4 |
| `UNIQUEKEY` | 0 arguments | 4 |
| `CacheBucketList` | 1 argument | 3 |

## Catalogue entries by corpus observation

### Expression calls recognized in T24

`@`, `ABS`, `ABSS`, `ADDS`, `ALPHA`, `ASCII`, `ASSIGNED`, `BITAND`, `BITNOT`, `BITOR`,
`BITXOR`, `BYTELEN`, `CALLC`, `CALLONEXIT`, `CATS`, `CHANGE`, `CHAR`, `CHDIR`,
`CHECKSUM`, `COL2`, `COMPARE`, `CONVERT`, `COUNT`, `COUNTS`, `DATE`, `DCOUNT`,
`DECRYPT`, `DELETE`, `DIV`, `DIVS`, `DOWNCASE`, `DQUOTE`, `DROUND`, `DTX`, `DYNTOXML`,
`EBCDIC`, `ENCRYPT`, `EQS`, `EREPLACE`, `EXP`, `EXTRACT`, `FIELD`, `FIELDS`, `FILEINFO`,
`FMT`, `FMTS`, `FOLD`, `GETENV`, `GROUP`, `GTS`, `ICONV`, `ICONVS`, `INDEX`, `INDICES`,
`INMAT`, `INSERT`, `INT`, `IOCTL`, `ISALNUM`, `ISALPHA`, `ISDIGIT`, `ITYPE`,
`JBASECOREDUMP`, `JBASESubroutineExist`, `KEYIN`, `LEFT`, `LEN`, `LENDP`, `LES`, `LN`,
`LOWCASE`, `LOWER`, `MATCHFIELD`, `MAXIMUM`, `MINIMUM`, `MOD`, `MULS`, `NEG`, `NEGS`,
`NES`, `NOT`, `NUM`, `OCONV`, `OCONVS`, `PUTENV`, `PWR`, `QUOTE`, `RAISE`,
`RECORDLOCKED`, `REM`, `REMOVE`, `REPLACE`, `REUSE`, `RIGHT`, `RND`, `SDIV`, `SENTENCE`,
`SEQ`, `SMUL`, `SORT`, `SPACE`, `SPACES`, `SPLICE`, `SQRT`, `SQUOTE`, `STATUS`, `STR`,
`SUBS`, `SUBSTRINGS`, `SUM`, `SUMMATION`, `SWAP`, `SYSTEM`, `TIME`, `TIMEDATE`,
`TIMESTAMP`, `TRIM`, `TRIMB`, `TRIMBS`, `TRIMF`, `TRIMS`, `UNASSIGNED`, `UNIQUEKEY`,
`UPCASE`, `UTF8`, `VALIDATE_PRODUCT_LICENSE`, `XMLTODYN`, `XMLTOXML`, `XTD`

### Expression calls with no recognized call in T24

`ACOS`, `ANDS`, `ASIN`, `ATAN`, `BITCHANGE`, `BITCHECK`, `BITLOAD`, `BITRESET`,
`BITSET`, `BITTEST`, `CHANGETIMESTAMP`, `CHARS`, `COL1`, `CONSUME_METRICS_LICENSE`,
`CONTROLCHAR`, `COS`, `CRC`, `DELENV`, `DIR`, `ERRTEXT`, `FADD`, `FCMP`, `FDIV`, `FFIX`,
`FFLT`, `FMUL`, `FSUB`, `GES`, `GETCWD`, `GETUSERGROUP`, `GETUSERNAME`, `IFS`, `IN`,
`ISCNTRL`, `ISGRAPH`, `ISLOWER`, `ISPRINT`, `ISPUNCT`, `ISSPACE`, `ISUPPER`, `ISXDIGIT`,
`JQLCOMPILE`, `JQLEXECUTE`, `JQLFETCH`, `JQLGETPROPERTY`, `JQLPUTPROPERTY`, `LATIN1`,
`LENS`, `LENSDP`, `LOCALDATE`, `LOCALTIME`, `LTS`, `MAKETIMESTAMP`, `MODS`, `NOTS`,
`NUMS`, `ORS`, `PERROR`, `REGEXP`, `SADD`, `SCMP`, `SELECTINFO`, `SEQS`, `SIN`,
`SOUNDEX`, `SPOOLER`, `SSUB`, `STRS`, `TA`, `TAN`, `TIMEDIFF`, `TRANS`, `TRANSQUERY`,
`TRANSSYNC`, `TRIMFS`, `VALIDATE_METRICS_LICENSE`, `XLATE`, `XML.ADD.NODE`,
`XML.ADD.TEXT`, `XML.GET.TAG.VALUE`, `XML.VALIDATE`

### JBC.h declarations recognized in T24

`CALLJEE`, `CacheBucketList`, `CacheClear`, `CacheDelete`, `CacheExists`, `CacheGet`,
`CachePut`, `CacheStats`, `GetProperty`, `JBASEGetInode`, `JBASEGetPidFromPort`,
`JEEActivate`, `JEEOpen`, `Logger`, `LoggerDescribe`, `LoggerPrint`, `MONEndUnitOfWork`,
`MONStartUnitOfWork`

### JBC.h declarations with no recognized call in T24

`BuildFileList`, `CacheClearAll`, `CacheClearStats`, `CacheGetOption`, `CacheKeyList`,
`CacheSetOption`, `JBASEAccess`, `JBASEAssertEquals`, `JBASEAssertTrue`, `JBASECALLC`,
`JBASECanonicalInput`, `JBASECheckRemote`, `JBASEGetDevInode`, `JBASEGetPortFromPid`,
`JBASEReturnLockInfo`, `JBASEScanfileEnd`, `JBASEScanfileInit`, `JBASEScanfileRead`,
`JBASETHREADCreate`, `JBASETHREADStatus`, `JBASEThreadGetRootStatus`,
`JBASEThreadSendMessage`, `JBASEThreadSetRootStatus`, `JBASEUserProfile`, `JEEClose`,
`JEEOpenSSL`, `LoggerDebugPrint`, `LoggerVerbosePrint`, `MONAddRepetitiveUnitOfWork`,
`MONAddSingleUnitOfWork`, `MONCurrentUnitOfWork`, `MONDump`, `MONIsInsideUnitOfWork`,
`MONIsUnitOfWorkMonitored`, `PutProperty`

### Recognized calls outside the catalogues

`JBASE_utf8_convert_var_codepage_to_utf8_BBB` (defc), `JBASE_utf8_setpage_IIS` (defc),
`JIMITraceOff` (defc), `JIMITraceOn` (defc)

Counts reflect calls recognized by jbcc after include and equate expansion.
A call in a shared include can contribute to several units. A zero count
means this scan found no recognized call. Rejected units can contribute
observations up to the first compiler diagnostic. The scan covers
expression calls and declared external C calls. Statically referenced
snippets are recorded in JSON as leads for test review. The runtime table
links to reviewed assertions. Other runtime evidence is unreviewed.
