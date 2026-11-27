# Releasing jbcc

A release publishes jbcc to PyPI and then moves three other repositories
to it: the playground, the guide's Run buttons and the organisation front
page. Do the steps in order; each repository change goes through a pull
request. Replace `X.Y.Z` with the new version.

## 1. Prepare the release in jbcc

On a branch such as `release/jbcc-X.Y.Z`:

1. Set `version = "X.Y.Z"` in `pyproject.toml`. `uv version --short`
   should print it.
2. In `CHANGELOG.md`, rename `## Unreleased` to `## X.Y.Z (YYYY-MM-DD)`
   and tidy the entries into `### Added` and `### Changed`, most important
   first.
3. Add a dated entry at the top of `NEWS.md` that links to
   `https://pypi.org/project/jbcc/X.Y.Z/`.
4. If the tested corpora changed, update the sentence in `README-PYPI.md`,
   which becomes the PyPI description.
5. Check the build:

   ```sh
   just test-parallel
   uv build -o /tmp/jbcc-dist
   just check-dist /tmp/jbcc-dist
   ```

   Both distributions must pass `twine check --strict`. List the wheel
   (`unzip -l`) if a release adds package data, such as
   `jbcc/include/JBC.h`.
6. Open a pull request, then merge it.

## 2. Publish to PyPI

From a clean `main` that matches `origin/main`:

```sh
git checkout main && git pull --ff-only
just publish
```

`just publish` tags `vX.Y.Z` and pushes the tag. The tag starts the
**Publish jbcc** workflow (`.github/workflows/publish.yml`), which builds
the distributions and uploads them with PyPI Trusted Publishing; no token
is involved. Watch it:

```sh
gh run watch "$(gh run list --workflow 'Publish jbcc' --limit 1 --json databaseId --jq '.[0].databaseId')" --exit-status
```

Then read the wheel's URL and SHA-256, which the playground pins:

```sh
curl -s https://pypi.org/pypi/jbcc/X.Y.Z/json | python3 -c "
import json, sys
for u in json.load(sys.stdin)['urls']:
    print(u['filename'], u['digests']['sha256'], u['url'])"
```

The JSON API sees a new release at once, but `uvx jbcc@X.Y.Z` can fail
with "no version of jbcc==X.Y.Z" for a few minutes while the package
index catches up. Retry with `uvx --refresh jbcc@X.Y.Z --run hello.b`.

## 3. Update the playground (jbc-playground)

On a branch such as `chore/jbcc-X.Y.Z`:

1. In `jbcc-wheel.mjs`, set `version`, the `files.pythonhosted.org` path
   in `url` and `sha256` from the JSON above.
2. Update the version in `README.md` ("the pinned `jbcc X.Y.Z` Python
   wheel").
3. Regenerate the editor's words with `just words`. It needs
   `uvx jbcc==X.Y.Z`; while the index lags, run the same tool on the
   downloaded wheel after checking its SHA-256:

   ```sh
   uvx --from ./jbcc-X.Y.Z-py3-none-any.whl python tools/jbc-words.py > web/jbc-words.json
   ```

4. Run `just test`, which builds the site and runs the browser suite.
5. Open a pull request and merge it. The **Publish playground** workflow
   deploys `main` to GitHub Pages. Check that the header of
   https://online.jbc-lang.org/ shows `jbcc X.Y.Z`.

## 4. Update the guide's Run buttons (jbc-language)

On a branch such as `runnable-X.Y.Z`:

1. Set `JBCC_VERSION = "X.Y.Z"` in `check_examples.py`.
2. Run `just examples`, which rewrites `site/runnable.txt`. Compare it
   with the previous version: a block should lose its button only for a
   reason you can explain.
3. Update the count in `README.md` ("In <month>, with jbcc X.Y.Z, N of
   the 1,016 blocks qualified").
4. Open a pull request against `master` and merge it.

## 5. Update the organisation front page (jbc-lang/.github)

In `profile/README.md`, update the link to `jbcc X.Y.Z` and, if they
changed, the tested corpora. Open a pull request and merge it.
