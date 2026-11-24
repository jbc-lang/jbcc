# Sources for jbcc

This index records the references used to investigate jBC syntax, runtime
behavior, and T24 compatibility. The [README](README.md#implemented-subset)
links to the relevant chapters for implemented features. The
[plan](PLAN.md) records individual probes, provisional choices, and
corpus results. Search filters below can be combined with a construct
name, such as `site:static.zumasys.com "JBCEMULATE"`.

## jBC and T24 references

| Source | Search filter | What we used it for |
|---|---|---|
| jBC Programmers Reference Guide | `site:jbc-lang.org` | Unofficial guide to syntax, examples, and TAFC/TAFJ release differences. The local source is `temenos-documentation/jBC_Programmers_Reference_Guide.markdown` in the sibling checkout. [Published guide](https://jbc-lang.org/), [chapter index](https://jbc-lang.org/llms.txt) |
| jbc-language grammar investigation | `site:github.com/jbc-lang/jbc-language` | Main jBC and jpp grammars, lexer keyword table, expression functions, and the cross-reference between `JBC.h` prototypes and guide chapters. The grammar provenance lists hashes of the original inputs. [Grammar and function reference](https://github.com/jbc-lang/jbc-language/tree/master/spec), [investigation PR](https://github.com/jbc-lang/jbc-language/pull/11) |
| Zumasys jBASE documentation archive | `site:static.zumasys.com` | jBC statements and functions, emulation settings, record locking, and terminal and account behavior. [Statement and function index](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/JBC1.htm), [CALL](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/jbc2_CALL.htm), [emulation](https://static.zumasys.com/jbase/r99/knowledgebase/manuals/3.0/30manpages/man/sup12_EMULATION.htm), [record locking](https://static.zumasys.com/jbase/r99/knowledgebase/howto/general/common/RecordLocking.htm) |
| Rocket Software jBASE documentation | `site:docs.rocketsoftware.com jBASE` | jBASE 5.9 and 6.2 comparisons, including INPUT, emulation, GROUP, and REWIND. [5.9 INPUT](https://docs.rocketsoftware.com/bundle/jbase_lib_59/page/hpy1666031229329.html), [5.9 emulation](https://docs.rocketsoftware.com/bundle/jbase_lib_59/page/ryu1684869638605.html), [6.2 GROUP](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/group_function.html), [6.2 REWIND](https://docs.rocketsoftware.com/bundle/jbase_lib_62/page/topics/rewind_statement.html) |
| Temenos T24 Programming Standards | `site:acosani.it "T24 Programming Standards"` | T24 conventions for routines, shared variables and inserts, and the context for helpers such as SEQX. [Temenos manual mirrored by acosani.it](https://www.acosani.it/infobasic/libri/T24%20Programming%20Standards.pdf) |

## Related MultiValue dialects and data tables

These sources explain behavior in named dialects or supply provisional
models where the jBC guide leaves details open. The implementation notes
identify where jbcc draws on them.

| Source | Search filter | What we used it for |
|---|---|---|
| IBM UniVerse BASIC Reference Guide | `site:publibfp.boulder.ibm.com c1942790` | Cross-checks for INPUT, LENDP, SUMMATION, and terminal behavior. [IBM archived PDF](https://publibfp.boulder.ibm.com/epubs/pdf/c1942790.pdf) |
| IBM InfoSphere Information Server documentation | `site:ibm.com/docs` | Comparisons for GETARG, READT, and TTYGET. [GETARG](https://www.ibm.com/docs/en/iis/11.7.0?topic=functions-getarg-statement), [READT](https://www.ibm.com/docs/en/iis/11.3.0?topic=functions-readt-statement), [TTYGET](https://www.ibm.com/docs/en/iis/11.7.0?topic=functions-ttyget-statement) |
| Rocket UniVerse BASIC documentation | `site:docs.rocketsoftware.com UniVerse BASIC` | Additional UniVerse BASIC cross-checks. [UniVerse BASIC User Guide](https://docs.rocketsoftware.com/bundle/universebasicuser_ug_1221/page/sat1687881202320.html) |
| InterSystems Caché MultiValue Basic Reference | `site:docs.intersystems.com "MultiValue Basic"` | Comparisons for TRIMS and MultiValue system variables. [TRIMS](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_ftrims), [system variables](https://docs.intersystems.com/latest/csp/docbook/DocBook.UI.Page.cls?KEY=RVBS_gsysvariables) |
| OpenQM reference | `site:krowemoh.com/static "qm.pdf"` | Provisional rules for MAT assignments between unequal matrix shapes. [OpenQM manual mirror](https://krowemoh.com/static/qm.pdf) |
| Unicode Consortium character mappings | `site:unicode.org CP037` | The published IBM US/Canada EBCDIC mapping used for the runtime's CP037 conversion tables. [CP037 mapping](https://www.unicode.org/Public/MAPPINGS/VENDORS/MICSFT/EBCDIC/CP037.TXT) |

During the source audit, the Zumasys archive returned a certificate error
on a direct HTTPS request, though indexed copies were available. The
OpenQM PDF link redirected to the mirror's login page.

## Local source and runtime evidence

| Local resource | What we used it for |
|---|---|
| `~/Downloads/jbc/` | The reference implementation snapshot. `jbc_lexer.l` and `jbc_parser.y` describe the main language, and `jpp_lexer.l` and `jpp_parser.y` describe preprocessing. `jcgenc.c` shows C lowering and `JBC.h` supplies equates and DEFC declarations. The standalone `jbccom` build identifies itself as 201015.001. Its probes establish what C the compiler emits under the chosen emulation. |
| `~/Downloads/PB201214-linux/` and `~/Downloads/PB201214-aix/` | TAFC distributions at PB201214.0.0.0, change level 106034. They supply the headers used by the corpus checker, including `JBC.h`, `jportB.h`, and `jimiB.h`. The two packages have identical `JBC.h` files. Linux was used for a runtime probe in Prime mode that linked and then stopped at the vendor's licensed-user limit. |
| `~/Downloads/t24/` | The local T24 corpus, including program and routine units and their include fragments. It establishes how constructs appear in application sources and provides a translation-to-C regression check. |
| `tests/programs/` and `tests/snippets/` | The banner and quine supplied by the user, plus jbcc's executable regression fixtures. These check the behavior of programs generated by jbcc. |

Record the document version, emulation setting, or reference snapshot for
new findings. A source scan measures syntax and translation coverage.
Runtime claims should cite an executed probe, a documented result, or a
provisional implementation decision.

## Test and probe tooling

- The fixture layout was compared with the Rust compiler's UI tests.
  [Rust Compiler Development Guide](https://rustc-dev-guide.rust-lang.org/tests/ui.html)
- pytest-xdist runs the complete suite in parallel. Testmon is useful for
  local iteration. Its dependency selection skipped an intentionally
  changed `.stdout` file in a temporary jbcc checkout, so use the full
  parallel run before committing. [pytest-xdist](https://pytest-xdist.readthedocs.io/en/stable/),
  [Testmon](https://www.testmon.org/), [Testmon compatibility notes](https://testmon.net/)
- The vendor Linux probe used an x86-64 Debian container on OrbStack.
  Debian supplied GCC and ncurses 5. The CentOS archive supplied the
  `libcrypto.so.10` required by the vendor runtime.
  [CentOS 7 OpenSSL package](https://vault.centos.org/7.9.2009/updates/x86_64/Packages/openssl-libs-1.0.2k-26.el7_9.x86_64.rpm)
