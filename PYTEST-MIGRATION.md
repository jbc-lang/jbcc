# Pytest migration

Migrate [tests/test_compiler.py](tests/test_compiler.py) in groups.
The baseline is 561 collected tests, including 183 snippet cases.
Keep this count through the framework conversion. Parametrizing
subtests later can increase the count.

## Shared fixtures and snippet runner

- [x] Record the baseline collection with `pytest --collect-only -q`
  and run the full suite with `just test-parallel`.
- [x] Introduce pytest fixtures based on `tmp_path` for each test's
  working directory and generated files.
- [x] Share the existing CLI, C99 build, and execution setup with the
  migrated tests. Preserve compiler flags, timeouts, environment
  overrides, and byte-for-byte output checks.
- [x] Replace the generated `SnippetTest` methods with one parametrized
  test. Use the source filename as its test ID and keep one case per
  `.b` and `.stdout` pair.
- [x] Verify all 183 snippet cases and the full 561-test collection.

## Compiler tests

Convert one behavior group per commit. Run its focused checks and
verify collection before moving to the next group.

- [x] Compiler diagnostics, preprocessing, and source encoding.
- [x] Built-ins, arithmetic, strings, and dynamic arrays.
- [x] Control flow, variable assignment, matrices, and `COMMON`.
- [x] Routine calls, functions, linkage, and the compiler driver.
- [x] Corpus reporting and external backend diagnostics.
- [ ] File I/O, record operations, saved lists, and locks.
- [ ] Command execution, invocation, session state, and user statistics.
- [ ] Clocks, terminal input, PTYs, and process lifecycle.
- [ ] Verify the full 561-test suite after the framework conversion.

## Parametrization and test commands

- [ ] Parametrize fixed variants with independent setup and give them
  descriptive case IDs. Keep loops that deliberately share a binary,
  process, terminal, or file state.
- [ ] Verify the new collection count against the migrated subtests.
- [ ] Make `just test` run pytest and retain `just test-parallel` for
  xdist. Update the README and remove the legacy unittest test command.
- [ ] Run the final suite through both recipes and confirm that they
  collect and pass the same cases.
