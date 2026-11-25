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
  A local T24 corpus may exist at `../t24-extract`; read its AGENTS.md.
- Put static jBC test source in checked-in `.b` files by default, including
  for diagnostics, multiple sources, setup or side effects. Generate jBC
  source in Python only when the test needs to construct or vary it.
- Place single-source tests that check only stdout and successful execution
  in `tests/snippets/` as `.b` and `.stdout` pairs. Use Python to drive
  tests that need additional setup or assertions.
- Centralize jBC value conversions in the runtime so generated C preserves
  jBC semantics. Make test doubles explicit and report unsupported services
  at their call sites.
- Document build and test commands as they become available. Use
  Conventional Commits with an imperative summary.
