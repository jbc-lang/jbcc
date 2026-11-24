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
