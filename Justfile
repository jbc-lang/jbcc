set positional-arguments

# List available recipes.
default:
    @just --list

# Sort imports and format the Python sources.
format:
    uvx ruff check --select I --fix jbcc .
    uvx ruff format jbcc .

# Check import order and Python formatting.
check:
    uvx ruff check --select I jbcc .
    uvx ruff format --check jbcc .

# Run the compiler and native execution tests with pytest.
test *args:
    uvx --from 'pytest>=9,<10' pytest "$@"

# Run the same tests in parallel, optionally selecting tests with pytest flags.
test-parallel jobs="auto" *args:
    @jobs="$1"; shift; uvx --from 'pytest>=9,<10' --with pytest-xdist pytest -n "$jobs" "$@"

# Show the package version in pyproject.toml.
version:
    @uv version --short

# Bump the package version in pyproject.toml.
bump part="patch":
    uv version --frozen --bump "$1"

# Build the PyPI source distribution and wheel.
dist directory="dist":
    uv build --no-sources --out-dir "$1"

# Check the source distribution and wheel for the current version.
check-dist directory="dist":
    @version=$(uv version --short); uvx twine check --strict "$1/jbcc-$version.tar.gz" "$1/jbcc-$version-py3-none-any.whl"

# Push the version tag to start the release workflow.
publish:
    #!/usr/bin/env sh
    set -eu
    if [ "$(git branch --show-current)" != main ] || [ -n "$(git status --porcelain --untracked-files=no)" ]; then
        echo 'Publish from a clean main branch.' >&2
        exit 1
    fi
    git fetch origin main
    if [ "$(git rev-parse HEAD)" != "$(git rev-parse origin/main)" ]; then
        echo 'Sync main with origin before publishing.' >&2
        exit 1
    fi
    version=$(uv version --short)
    tag="v$version"
    if git show-ref --verify --quiet "refs/tags/$tag"; then
        if [ "$(git rev-parse "refs/tags/$tag^{commit}")" != "$(git rev-parse HEAD)" ]; then
            echo "Tag $tag already points to another commit." >&2
            exit 1
        fi
    else
        git tag -a "$tag" -m "Release jbcc $version"
    fi
    git push origin "refs/tags/$tag"

# Build a native executable from one or more sources.
build output +sources:
    @out="$1"; shift; ./jbcc --exe -o "$out" "$@"

# Translate one or more sources into a standalone C file.
emit-c output +sources:
    @out="$1"; shift; ./jbcc -o "$out" "$@"

# Compile and run a program in a temporary directory.
run +sources:
    @./jbcc --run "$@"

# Run the terminal animation. Press Enter to stop.
banner: (run "tests/programs/banner.b")

# Print the quine's source by executing it.
quine: (run "tests/programs/quine.b")

# Run the two-source T24-style routine example.
routine: (run "tests/routines/caller.b" "tests/routines/get.status.b")

# Scan a local source corpus and write JSON to stdout.
corpus directory jobs="8":
    @python3 tools/check_corpus.py "$1" -j "$2"

alias playground-static := playground

# Build and serve the browser playground.
playground port="18766":
    cd playground && bun install --frozen-lockfile
    bun playground/build-static.mjs
    python3 -m http.server {{port}} --bind 127.0.0.1 --directory dist/playground
