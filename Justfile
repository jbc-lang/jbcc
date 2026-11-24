set positional-arguments

# List available recipes.
default:
    @just --list

# Run the compiler and native execution tests with the Python standard library.
test:
    python3 -B -m unittest discover -s tests -v

# Run the same tests in parallel, optionally selecting tests with pytest flags.
test-parallel jobs="auto" *args:
    @jobs="$1"; shift; uvx --with pytest-xdist pytest -n "$jobs" "$@"

# Build a native executable from one or more sources.
build output +sources:
    @out="$1"; shift; ./jbcc --exe -o "$out" "$@"

# Translate one or more sources into a standalone C file.
emit-c output +sources:
    @out="$1"; shift; ./jbcc -o "$out" "$@"

# Compile and run a program in a temporary directory.
run +sources:
    #!/usr/bin/env sh
    set -eu
    work=$(mktemp -d)
    trap 'rm -rf "$work"' EXIT
    ./jbcc --exe -o "$work/program" "$@"
    "$work/program"

# Run the terminal animation. Press Enter to stop.
banner: (run "tests/programs/banner.b")

# Print the quine's source by executing it.
quine: (run "tests/programs/quine.b")

# Run the two-source T24-style routine example.
routine: (run "tests/routines/caller.b" "tests/routines/get.status.b")

# Scan a local source corpus and write JSON to stdout.
corpus directory jobs="8":
    @python3 tools/check_corpus.py "$1" -j "$2"
