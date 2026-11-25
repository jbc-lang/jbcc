# Publish jbcc on PyPI

The first release should let someone with uv compile a local jBC file from
any working directory. Both native modes, `--exe` and `--run`, need a
C99 compiler on `PATH`. jbcc uses `cc` by default and accepts `CC` and
`CC_FLAGS` overrides.

```sh
uvx jbcc hello.b -o hello.c
uvx jbcc --exe -o hello hello.b
uvx jbcc --run hello.b
```

Use jbcc as both the PyPI distribution name and the command name. On
2026-11-25, PyPI's JSON and Simple endpoints both returned 404 for jbcc.
Recheck the name before configuring the publisher. If PyPI accepts it,
the first upload creates the project. [uv tool execution](https://docs.astral.sh/uv/guides/tools/).

## 1. Package the compiler

- [x] Move the existing implementation into `src/jbcc/compiler.py` and
  keep `./jbcc` as a thin checkout launcher. Register the same `main()`
  function with `[project.scripts]` as `jbcc = "jbcc.compiler:main"`.
- [x] Move `runtime/jbc.c` into the package and read it relative to the
  compiler module. Update `tools/check_corpus.py` to import the compiler and
  use the same runtime loader. It currently loads the root script via
  `runpy` and reads the C file separately. Preserve source-relative include
  lookup and caller-relative input, output, and execution paths.
- [ ] Add Hatchling build metadata to `pyproject.toml`, keeping the Ruff
  settings. Use `0.1.0` for the first release and `requires-python = ">=3.8"`
  if the installed smoke tests pass on Python 3.8. Keep runtime Python
  dependencies empty. Include the project URLs, README, MIT license, and
  Unicode notice for the bundled CP037 data.
- [ ] Use explicit file inclusion for the wheel and source distribution.
  Ship the compiler, C runtime, and packaging documents. Keep local corpus
  inputs, vendor files, credentials, caches, and build output out of both
  archives. Update the README and third-party notice if they refer to a
  moved source path.
  [Packaging metadata](https://packaging.python.org/en/latest/guides/writing-pyproject-toml/).
  [Hatch build configuration](https://hatch.pypa.io/dev/build/).

## 2. Verify the release artifacts

- [ ] Run `just check` and `just test-parallel` through the checkout launcher.
  Run the R07 and R10 syntax checks with the local corpora to catch regressions
  in the shared runtime loader and corpus checker.
- [ ] Run `uv build` from a clean checkout and `uvx twine check dist/*`.
  Inspect the file lists of both archives. Confirm the wheel is
  platform-independent, contains the C runtime and license files, and
  declares the `jbcc` entry point. Build a wheel from the source archive
  and check it contains the same runtime and entry point.
- [ ] In a temporary directory outside the checkout with no `PYTHONPATH`,
  copy in a checked-in example and run the installed command from each
  wheel. Verify C emission, `--exe`, `--run` with and without `-o`, and
  source-relative includes. Check exact stdout and exit status. Cover
  macOS and Linux. On the minimum supported Python version, verify both
  installation from the wheel and a build from the source archive.
- [ ] Use an absolute wheel path to exercise uv's tool installation before
  upload. [Building packages with uv](https://docs.astral.sh/uv/guides/package/).

  ```sh
  uvx --from /absolute/path/to/dist/jbcc-0.1.0-py3-none-any.whl \
    jbcc --run hello.b
  ```

## 3. Rehearse and publish

- [ ] Add a GitHub Actions release workflow that builds and checks the
  distributions before handing the same files to a separate upload job.
  Use a deliberate release trigger with a tag that matches the package
  version, such as `v0.1.0`. Grant `id-token: write` to the upload job only.
- [ ] Configure separate pending Trusted Publishers on TestPyPI and PyPI
  for `jbc-lang/jbcc`. Match each publisher's workflow filename and GitHub
  environment to the release configuration. Use PyPA's publishing action
  with OIDC so releases can run without a stored upload token.
  [Creating a project with Trusted Publishing](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/).
  [Publishing from GitHub Actions](https://docs.pypi.org/trusted-publishers/using-a-publisher/).
- [ ] Publish to TestPyPI first. From outside the checkout, run
  `uvx --default-index https://test.pypi.org/simple/ jbcc@0.1.0 --run hello.b`
  and check the output. Verify that the project page renders the README
  and identifies the repository and license. Check links to examples and
  other repository files from the rendered PyPI description.
- [ ] After the rehearsal passes, publish the verified distributions to
  production PyPI. Use a fresh uv cache and a temporary working directory
  to verify `uvx jbcc --help`, `uvx jbcc --run hello.b`, and the pinned
  invocation `uvx jbcc@0.1.0 --run hello.b`.
- [ ] Add the verified `uvx` commands and the PyPI link to the README.
  If a release needs correcting, publish a new version and yank the
  faulty version if needed. [PyPI yanking guidance](https://docs.pypi.org/project-management/yanking/).
