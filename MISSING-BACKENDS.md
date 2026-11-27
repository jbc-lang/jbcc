# Missing backends

Features jbcc parses and translates, but cannot run, because they need a
service jbcc does not have. Each one reports its source location when
execution reaches it (or at translation, where marked), so a program that
never uses one is not affected. LANGUAGE-GAPS.md lists smaller gaps and
deliberate differences from TAFC PB201214.

Entries are grouped by the backend they need.

## How much T24 needs each one

Files in the R13 and R19 corpora that contain the word (2026-11-27; a word
match, so comments count too):

| Feature | Files |
|---|---|
| `INDICES` | 205 |
| `CALLJ` | 93 |
| `ITYPE` | 69 |
| `DYNTOXML` | 27 |
| `XMLTODYN` | 17 |
| `TRANSTART` | 11 |
| `READXML` | 5 |
| `VALIDATE_PRODUCT_LICENSE` | 4 |
| `JBASECOREDUMP` | 3 |
| `DATELOCALETOGREGORIAN` | 1 |

## Database files

jbcc keeps records only in in-memory files, named at translation time with
`--memory-file` and `--memory-dict`. They start empty in every run.

| Feature | What is missing | Message |
|---|---|---|
| Persistent jBASE files (J4, JR) | Files that outlive the process, shared between programs | `OPEN` of an unnamed file takes ELSE |
| `INDICES(file, ...)` | Secondary indexes | `INDICES requires a secondary-index backend` |
| `ITYPE(descriptor)` | Compiled dictionary I-types | `ITYPE requires a compiled dictionary backend` |
| `MATREAD ... LOCKED` | Lock clauses on MATREAD | at translation: `MATREAD LOCKED requires a locking file backend` |
| `READU ... WAIT` | Locks that wait for a timeout | at translation: `READU WAIT requires a backend with timed locks` |
| `TRANSTART`, `TRANSEND`, `TRANSABORT`, `TRANSACTION ...` | Transaction journal and rollback | `... requires a transaction backend` |

## jBASE commands

`EXECUTE`, `PERFORM` and `CHAIN` run a command with `/bin/sh -c`. jBASE
shell and jQL commands, such as `CREATE-FILE`, `SELECT`, `COUNT`, `LIST`,
`SORT` and `SH`, are not available unless a program of that name is on
`PATH`. TAFC PB201214 runs commands without a shell (LANGUAGE-GAPS.md).

## XML

| Feature | Message |
|---|---|
| `DYNTOXML`, `DYNTOXMLEXT`, `XMLTODYN`, `XMLTOXML` | `... requires an XML backend` |
| `READXML`, `READXMLU` | `... requires an XML backend` |

These need an XML parser and an XSLT processor.

## Encryption

`ENCRYPT` and `DECRYPT` implement ROT13 (1), XOR11 (2), BASE64 (4) and the
Base64 mask bit. The cipher methods need a cryptography library:

| Method (JBC.h) | Value |
|---|---|
| `JBASE_CRYPT_GENERAL` | 0 |
| `JBASE_CRYPT_RC2` | 3 |
| `JBASE_CRYPT_DES` | 5 |
| `JBASE_CRYPT_3DES` | 6 |
| `JBASE_CRYPT_BLOWFISH` | 7 |
| `JBASE_CRYPT_AES` | 8 |

The same methods with the Base64 mask, such as `JBASE_CRYPT_AES_BASE64`,
are missing too. Message: `ENCRYPT requires a backend for this method` (or
`DECRYPT`). TAFC's results would have to be reproduced byte for byte,
including key derivation and padding, so each method needs TAFC probes.

## Calendars

| Feature | Message |
|---|---|
| `DATELOCALETOGREGORIAN` | `DATELOCALETOGREGORIAN requires a calendar backend` |
| `DATEGREGORIANTOLOCALE` | `DATEGREGORIANTOLOCALE requires a calendar backend` |

These need locale calendars (for example Hijri or Thai), as ICU provides.

Named time zones also need a zone database. The native runtime uses the
host's; the playground's WASI runtime has none, so only an empty zone,
`UTC` and `GMT` work there.

## Java

| Feature | Message |
|---|---|
| `CALLJ` | `CALLJ requires a JVM backend` |

## The jBASE C runtime

| Feature | Message |
|---|---|
| `DEFC` functions other than the `JBC.h` cache functions | at translation: `C function '...' requires the jBASE C runtime` |

The cache functions (`CacheGet`, `CachePut` and the rest) are implemented
in jbcc's runtime. Other `DEFC` functions are C code linked into TAFC
programs, which jbcc cannot see.

## Licensing, snapshots and the debugger

| Feature | Message |
|---|---|
| `VALIDATE_PRODUCT_LICENSE` | `VALIDATE_PRODUCT_LICENSE requires a licensing backend` |
| `JBASECOREDUMP` | `JBASECOREDUMP requires an application snapshot backend` |
| `DEBUG` | `DEBUG requires a jBC debugger` |

## T24 at run time

The T24 corpora translate in full (R13-CORPUS.md, R19-CORPUS.md), but
running T24 code needs T24 itself:

- T24 table operations (`F.READ`, `F.WRITE` and the R19 component calls)
  are checked against their declarations, not run.
- The `.tut` unit tests need their `.d` records and the routines they
  test. Running a first set of them is the next planned step (PLAN.md).
