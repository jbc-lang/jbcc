# Working on jbcc

Read README.md for the current milestone and its acceptance example.

- Develop the compiler in this repository. The grammar and guide are
  maintained in jbc-lang/jbc-language. When a rule changes, record which
  guide chapter, grammar production or source observation supports it.
- Implement each new language construct through the compiler entry point.
  For an executable snippet, translate it to C, compile it with the native C
  compiler and compare stdout and exit status. For invalid input, check the
  diagnostic and its source location.
- Keep test snippets small and independently authored. Record whether an
  expected result comes from a guide example, an observed reference run or
  a provisional project decision. Keep external source corpora local.
- Place self-contained, single-source success tests with expected stdout
  in `tests/snippets/` as `.b` and `.stdout` pairs. Use Python tests for
  diagnostics, multiple sources, setup or side effects.
- Centralize jBC value conversions in the runtime so generated C preserves
  jBC semantics. Make test doubles explicit and report unsupported services
  at their call sites.
- Document build and test commands as they become available. Use
  Conventional Commits with an imperative summary.
