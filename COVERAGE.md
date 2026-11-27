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

Reviewed runtime assertions are linked for 81 APIs. Repo snippets
reference 157 APIs and are indexed in JSON.

## Runtime evidence by form

| API | Form | Guide | T24 units | jbcc support | Runtime evidence |
|---|---|---|---:|---|---|
| `CALLJEE` | 2 arguments | [Guide](https://jbc-lang.org/pages/calljee.html) | 1 | backend required | Unreviewed |
| `CacheBucketList` | 1 argument | [Guide](https://jbc-lang.org/pages/cachebucketlist.html) | 3 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheClear` | 1 argument | [Guide](https://jbc-lang.org/pages/cacheclear.html) | 1 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheClearAll` | 0 arguments | [Guide](https://jbc-lang.org/pages/cacheclearall.html) | 0 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheClearStats` | 1 argument | [Guide](https://jbc-lang.org/pages/cacheclearstats.html) | 0 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheDelete` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachedelete.html) | 1 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheExists` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheexists.html) | 5 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheGet` | 2 arguments | [Guide](https://jbc-lang.org/pages/cacheget.html) | 4 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheGetOption` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachegetoption.html) | 0 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheKeyList` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachekeylist.html) | 0 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CachePut` | 3 arguments | [Guide](https://jbc-lang.org/pages/cacheput.html) | 5 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheSetOption` | 3 arguments | [Guide](https://jbc-lang.org/pages/cachesetoption.html) | 0 | call translates | [Guide example checked](tests/snippets/cache.b) |
| `CacheStats` | 2 arguments | [Guide](https://jbc-lang.org/pages/cachestats.html) | 3 | call translates | [Guide example checked](tests/snippets/cache.b) |
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
| `ACOS` | 1 argument | — | 0 | call translates | [Degrees returned (provisional) checked](tests/snippets/trigonometry-inverse.b) |
| `ANDS` | 2 arguments | [Guide](https://jbc-lang.org/pages/ands.html) | 0 | call translates | [Guide example and nulls checked](tests/snippets/logical-arrays.b) |
| `ASIN` | 1 argument | — | 0 | call translates | [Degrees returned (provisional) checked](tests/snippets/trigonometry-inverse.b) |
| `ATAN` | 1 argument | — | 0 | call translates | [Degrees returned (provisional) checked](tests/snippets/trigonometry-inverse.b) |
| `BITAND` | 2 arguments | [Guide](https://jbc-lang.org/pages/bitand.html) | 1 | call translates | [Signed 32-bit output checked](tests/snippets/bitand.b) |
| `BITCHANGE` | 1 argument | [Guide](https://jbc-lang.org/pages/bitchange.html) | 0 | call translates | [Guide example checked](tests/snippets/bit-table.b) |
| `BITCHECK` | 1 argument | [Guide](https://jbc-lang.org/pages/bitcheck.html) | 0 | call translates | [Table bits checked](tests/snippets/bit-table.b) |
| `BITLOAD` | 0 arguments | [Guide](https://jbc-lang.org/pages/bitload.html) | 0 | call translates | [Hexadecimal table checked](tests/snippets/bit-table.b) |
| `BITLOAD` | 1 argument | [Guide](https://jbc-lang.org/pages/bitload.html) | 0 | call translates | [Guide example load checked](tests/snippets/bit-table.b) |
| `BITNOT` | 1 argument | [Guide](https://jbc-lang.org/pages/bitnot.html) | 1 | call translates | [Unsigned 32-bit output checked](tests/snippets/bitand.b) |
| `BITOR` | 2 arguments | [Guide](https://jbc-lang.org/pages/bitor.html) | 3 | call translates | [Signed 32-bit output checked](tests/snippets/bitor.b) |
| `BITRESET` | 1 argument | [Guide](https://jbc-lang.org/pages/bitreset.html) | 0 | call translates | [Guide example and whole table checked](tests/snippets/bit-table.b) |
| `BITSET` | 1 argument | [Guide](https://jbc-lang.org/pages/bitset.html) | 0 | call translates | [Guide example and whole table checked](tests/snippets/bit-table.b) |
| `CHANGETIMESTAMP` | 2 arguments | [Guide](https://jbc-lang.org/pages/changetimestamp.html) | 0 | call translates | [Guide examples checked](tests/snippets/changetimestamp.b) |
| `CHARS` | 1 argument | [Guide](https://jbc-lang.org/pages/chars.html) | 0 | call translates | [Guide example checked](tests/snippets/array-character-functions.b) |
| `CHDIR` | 1 argument | [Guide](https://jbc-lang.org/pages/chdir.html) | 1 | call translates | [Directory change and failure checked](tests/io/chdir.b) |
| `DATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/date.html) | 669 | call translates | [Local date and epoch checked](tests/test_terminal.py) |
| `DECRYPT` | computed method | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | runtime support depends on method | Unreviewed |
| `DECRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `DECRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/decrypt.html) | 10 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `DECRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/decrypt.html) | 1 | backend required | Unreviewed |
| `DELENV` | 1 argument | — | 0 | call translates | [Removal and absent names checked](tests/test_session.py) |
| `DIR` | 1 argument | [Guide](https://jbc-lang.org/pages/dir.html) | 0 | call translates | [File, directory and missing path checked](tests/test_session.py) |
| `DYNTOXML` | 2 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `DYNTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/dyntoxml.html) | 3 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `ENCRYPT` | computed method | [Guide](https://jbc-lang.org/pages/encrypt.html) | 1 | runtime support depends on method | Unreviewed |
| `ENCRYPT` | method 1 (ROT13) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 0 | ROT13 implemented | [ROT13 output checked](tests/snippets/rot13.b) |
| `ENCRYPT` | method 4 (Base64) | [Guide](https://jbc-lang.org/pages/encrypt.html) | 8 | backend required | [Missing-backend diagnostic checked](tests/test_diagnostics.py) |
| `ENCRYPT` | method 6 | [Guide](https://jbc-lang.org/pages/encrypt.html) | 1 | backend required | Unreviewed |
| `FADD` | 2 arguments | [Guide](https://jbc-lang.org/pages/fadd.html) | 0 | call translates | [Guide example at PRECISION 7 checked](tests/snippets/float-arithmetic.b) |
| `FCMP` | 2 arguments | — | 0 | call translates | [Ordering (provisional) checked](tests/snippets/float-arithmetic.b) |
| `FDIV` | 2 arguments | [Guide](https://jbc-lang.org/pages/fdiv.html) | 0 | call translates | [Guide example checked](tests/snippets/float-arithmetic.b) |
| `FILEINFO` | 2 arguments | [Guide](https://jbc-lang.org/pages/fileinfo.html) | 15 | call translates | [Handle status and pathname checked](tests/test_io.py) |
| `FMUL` | 2 arguments | — | 0 | call translates | [Guide example checked](tests/snippets/float-arithmetic.b) |
| `FSUB` | 2 arguments | [Guide](https://jbc-lang.org/pages/fsub.html) | 0 | call translates | [Rounding to PRECISION checked](tests/snippets/element-functions.b) |
| `GETCWD` | 1 argument | [Guide](https://jbc-lang.org/pages/getcwd.html) | 0 | call translates | [Working directory after CHDIR checked](tests/io/chdir.b) |
| `GETENV` | 1 argument | [Guide](https://jbc-lang.org/pages/getenv.html) | 3 | call translates | [Environment lookup checked](tests/io/getenv.b) |
| `GETENV` | 2 arguments | [Guide](https://jbc-lang.org/pages/getenv.html) | 27 | call translates | [Environment lookup and output parameter checked](tests/io/getenv.b) |
| `GETUSERGROUP` | 1 argument | [Guide](https://jbc-lang.org/pages/getusergroup.html) | 0 | call translates | [Primary group number checked](tests/test_session.py) |
| `GETUSERNAME` | 1 argument | — | 0 | call translates | [Login name checked](tests/test_session.py) |
| `IFS` | 3 arguments | [Guide](https://jbc-lang.org/pages/ifs.html) | 0 | call translates | [Guide TAFC output checked](tests/snippets/logical-arrays.b) |
| `INDICES` | 1 argument | — | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INDICES` | 2 arguments | — | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `INMAT` | 0 arguments | [Guide](https://jbc-lang.org/pages/inmat.html) | 12 | call translates | [Latest matrix load count checked](tests/io/inmat.b) |
| `INMAT` | 1 argument | [Guide](https://jbc-lang.org/pages/inmat.html) | 3 | call translates | [Matrix bounds checked](tests/io/inmat.b) |
| `IOCTL` | 3 arguments | [Guide](https://jbc-lang.org/pages/ioctl.html) | 7 | call translates | [Filename query and output parameter checked](tests/test_io.py) |
| `ISALNUM` | 1 argument | [Guide](https://jbc-lang.org/pages/isalnum.html) | 1 | call translates | [ASCII letters and digits checked](tests/snippets/character-class-predicates.b) |
| `ISCNTRL` | 1 argument | [Guide](https://jbc-lang.org/pages/iscntrl.html) | 0 | call translates | [Guide example with @FM checked](tests/snippets/character-class-extended.b) |
| `ISGRAPH` | 1 argument | — | 0 | call translates | [ASCII graphic bytes checked](tests/snippets/character-class-extended.b) |
| `ISLOWER` | 1 argument | [Guide](https://jbc-lang.org/pages/islower.html) | 0 | call translates | [ASCII lower-case letters checked](tests/snippets/character-class-predicates.b) |
| `ISPRINT` | 1 argument | [Guide](https://jbc-lang.org/pages/isprint.html) | 0 | call translates | [Guide note with @FM checked](tests/snippets/character-class-extended.b) |
| `ISPUNCT` | 1 argument | — | 0 | call translates | [ASCII punctuation checked](tests/snippets/character-class-extended.b) |
| `ISSPACE` | 1 argument | [Guide](https://jbc-lang.org/pages/isspace.html) | 0 | call translates | [ASCII white space checked](tests/snippets/character-class-predicates.b) |
| `ISUPPER` | 1 argument | [Guide](https://jbc-lang.org/pages/isupper.html) | 0 | call translates | [ASCII upper-case letters checked](tests/snippets/character-class-predicates.b) |
| `ISXDIGIT` | 1 argument | — | 0 | call translates | [Hexadecimal digits checked](tests/snippets/character-class-extended.b) |
| `ITYPE` | 1 argument | [Guide](https://jbc-lang.org/pages/itype.html) | 7 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `JBASECOREDUMP` | 2 arguments | [Guide](https://jbc-lang.org/pages/jbasecoredump.html) | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `LENS` | 1 argument | [Guide](https://jbc-lang.org/pages/lens.html) | 0 | call translates | [Element lengths and marks checked](tests/snippets/element-functions.b) |
| `LENSDP` | 1 argument | — | 0 | call translates | [Element lengths checked](tests/snippets/array-character-functions.b) |
| `LOCALDATE` | 2 arguments | [Guide](https://jbc-lang.org/pages/localdate.html) | 0 | call translates | [UTC and zone dates checked](tests/snippets/timestamps.b) |
| `LOCALTIME` | 2 arguments | [Guide](https://jbc-lang.org/pages/localtime.html) | 0 | call translates | [UTC and zone times checked](tests/snippets/timestamps.b) |
| `MAKETIMESTAMP` | 3 arguments | [Guide](https://jbc-lang.org/pages/maketimestamp.html) | 0 | call translates | [UTC and fixed-offset zone values checked](tests/snippets/timestamps.b) |
| `MODS` | 2 arguments | [Guide](https://jbc-lang.org/pages/mods.html) | 0 | call translates | [Guide example and nulls checked](tests/snippets/logical-arrays.b) |
| `NOTS` | 1 argument | [Guide](https://jbc-lang.org/pages/nots.html) | 0 | call translates | [Element complements and marks checked](tests/snippets/element-functions.b) |
| `ORS` | 2 arguments | [Guide](https://jbc-lang.org/pages/ors.html) | 0 | call translates | [Guide example and nulls checked](tests/snippets/logical-arrays.b) |
| `PUTENV` | 1 argument | [Guide](https://jbc-lang.org/pages/putenv.html) | 13 | call translates | [Environment updates checked](tests/io/putenv.b) |
| `REGEXP` | 2 arguments | [Guide](https://jbc-lang.org/pages/regexp.html) | 0 | call translates | [Guide examples checked](tests/snippets/regexp.b) |
| `SADD` | 2 arguments | [Guide](https://jbc-lang.org/pages/sadd.html) | 0 | call translates | [Guide examples checked](tests/snippets/string-arithmetic.b) |
| `SCMP` | 2 arguments | — | 0 | call translates | [Ordering (provisional) checked](tests/snippets/string-arithmetic.b) |
| `SEQS` | 1 argument | [Guide](https://jbc-lang.org/pages/seqs.html) | 0 | call translates | [Guide example checked](tests/snippets/array-character-functions.b) |
| `SOUNDEX` | 1 argument | [Guide](https://jbc-lang.org/pages/soundex.html) | 0 | call translates | [Guide code table checked](tests/snippets/soundex.b) |
| `SSUB` | 2 arguments | [Guide](https://jbc-lang.org/pages/ssub.html) | 0 | call translates | [Exact difference checked](tests/snippets/string-arithmetic.b) |
| `STRS` | 2 arguments | [Guide](https://jbc-lang.org/pages/strs.html) | 0 | call translates | [Guide example checked](tests/snippets/array-character-functions.b) |
| `TAN` | 1 argument | [Guide](https://jbc-lang.org/pages/tan.html) | 0 | call translates | [Degrees and the guide example checked](tests/snippets/trigonometry-inverse.b) |
| `TIME` | 0 arguments | [Guide](https://jbc-lang.org/pages/time.html) | 385 | call translates | [Local clock checked](tests/test_terminal.py) |
| `TIMEDATE` | 0 arguments | [Guide](https://jbc-lang.org/pages/timedate.html) | 625 | call translates | [Local midnight rollover checked](tests/test_terminal.py) |
| `TIMEDIFF` | 3 arguments | [Guide](https://jbc-lang.org/pages/timediff.html) | 0 | call translates | [Masks 0 and 1 with signs checked](tests/snippets/timestamps.b) |
| `VALIDATE_PRODUCT_LICENSE` | 1 argument | — | 1 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTODYN` | 2 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 0 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTODYN` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltodyn.html) | 2 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |
| `XMLTOXML` | 3 arguments | [Guide](https://jbc-lang.org/pages/xmltoxml.html) | 3 | backend required | [Missing-backend diagnostic checked](tests/test_corpus.py) |

## Frequent T24 forms without a linked test

The JSON contains 32 observed forms with neither a reviewed runtime
assertion nor a snippet reference. The table shows up to ten forms,
ordered by the number of translation units.

| API | Form | T24 units |
|---|---|---:|
| `Logger` | 3 arguments | 34 |
| `JBASEGetPidFromPort` | 1 argument | 6 |
| `MONEndUnitOfWork` | 0 arguments | 4 |
| `MONStartUnitOfWork` | 1 argument | 4 |
| `ASCII` | 1 argument | 4 |
| `UNIQUEKEY` | 0 arguments | 4 |
| `GetProperty` | 2 arguments | 2 |
| `JBASE_utf8_convert_var_codepage_to_utf8_BBB` | 2 arguments | 2 |
| `JIMITraceOff` | 1 argument | 2 |
| `JIMITraceOn` | 3 arguments | 2 |

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
