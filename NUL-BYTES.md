# Byte 0 in strings: design

jbcc strings are NUL-terminated C strings, so a value cannot hold byte 0.
TAFC PB201214's can (`tests/tafc/char-bytes.b`):

```
CRT OCONV(CHAR(0):'A', 'MX'), LEN(CHAR(0):'A'), SEQ(CHAR(0))   → 0041 2 0
```

Today jbcc stops on `CHAR(0)` and `CHAR(256)`, stops reading INPUT,
CAPTURING and RETURNING data at a NUL byte, and ends MX decoding and
COLLECTDATA at one. T24 code shows no NUL bytes in strings, so this work is
for completeness and for programs that handle binary data.

## Constraints

- The runtime is 9,438 lines with 318 exported functions. It has 148
  `strlen` calls, 35 `strcmp`, 37 `strchr`, 11 `strstr`, 36 `strcpy`, 39
  `%s` formats and 14 `fputs`. The generated code passes `const char *`
  everywhere.
- **The collector keeps a buffer only when a live variable holds its start
  address** (`jbc_collect`, `held_in_storage`). So every value a variable
  holds is a C literal or the start of a runtime buffer. Pointers into the
  middle of a buffer exist only as temporaries inside one statement.
- Every buffer already ends with a NUL (`allocate(n)` reserves `n + 1`
  bytes), so code that does not know about embedded NUL bytes keeps
  working on the part before the first one.

## Options considered

1. **A value type carrying a length**, such as `struct { const char *bytes;
   size_t length; }`, through the runtime and the generated code. This is
   complete, but it changes all 318 functions and every emitted call at
   once, with no working state in between.
2. **A reserved stand-in byte for NUL**, translated on input and output.
   This is the smallest change, but LEN, SEQ, comparisons and CHAR(n) of
   the stand-in byte would all be wrong.
3. **A length in the buffer header that is known only when set**, chosen
   and described below. It works one function at a time, and every step
   leaves a working runtime.

## Design

```c
struct jbc_buffer {
    struct jbc_buffer *next;
    size_t length;          /* SIZE_MAX: unknown, use strlen */
    char text[];
};

size_t jbc_size(const char *value);                 /* exact byte count */
static char *allocate_sized(size_t length);         /* sets length */
```

- `allocate` leaves `length` as `SIZE_MAX`, because many callers fill less
  than they reserve. `jbc_size` then uses `strlen`, so all existing code
  keeps its current meaning.
- **Code that knows about NUL bytes** allocates with `allocate_sized`, or
  records the length once the buffer is filled.
- **Buffers with a known length go into a small pointer set**, a hash table
  keyed by the text address. The collector removes them when it frees
  them. `jbc_size(v)` looks `v` up only when the set is not empty, so
  programs without NUL bytes pay one branch.
- **Literals and pointers into buffers** are not in the set and use
  `strlen`. A function that can meet NUL bytes must not hand on a pointer
  into a buffer: it copies the part it returns into an `allocate_sized`
  buffer, which most of them already do.
- **Values without NUL bytes are unchanged:** a converted function gives
  the same result as before.
- **Unconverted functions** keep working on the text before the first NUL.
  That limit is reported as a difference until the function is converted.

## Stages

Stages 1 to 3 are done (`tests/tafc/nul-core.b`, `nul-arrays.b`). In
stage 3, `split_array_items` copies the whole sized array, and
`item_end`, `item_value` and `cursor_value` give an element as a sized
value only when the array holds byte 0, so other arrays keep the old fast
path; a 20,000-element LOCATE benchmark runs as fast as before. One change from the
plan: only a buffer that actually holds byte 0 records its length and
goes in the pointer set, so the set stays small, and every other buffer
is an ordinary C string.

Each stage is one pull request with TAFC probes (`tests/tafc/nul-*.b`)
recorded first, and `char-bytes.b` stays a known difference until stage 3.

1. **Foundation:**
   - add the header field, `allocate_sized`, `jbc_size`, the pointer set
     and collector support;
   - add a debug check (`-DJBC_CHECK_SIZES`) for a recorded length that
     disagrees with `strlen` on NUL-free text.

   Nothing visible changes.
2. **Core operations:**
   - CHAR and CHARS (`CHAR(0)`, `CHAR(256)`);
   - concatenation (`:`, `jbc_concat`), LEN, SEQ, substrings `[s,n]`,
     comparisons (`=`, `<`, etc., with `memcmp`);
   - CRT, PRINT and other output (`fwrite`);
   - `OCONV ... 'MX'` both ways, and MCP/MCNP.

   `char-bytes.b` matches TAFC.
3. **Dynamic arrays:**
   - extraction, INSERT, REPLACE, DELETE, `<>` assignment;
   - FIELD, GROUP, INDEX, COUNT, DCOUNT, CHANGE, EREPLACE, CONVERT, STR;
   - LOCATE, and the per-element functions that split on marks
     (`split_array_items`).
4. **Input and files:**
   - INPUT, KEYIN, CAPTURING, RETURNING, COLLECTDATA, RTNDATA and the list
     files;
   - OSREAD, OSWRITE, READSEQ, WRITESEQ, READBLK, WRITEBLK;
   - in-memory file records and keys.

   This removes the "cannot store a NUL byte" diagnostics.
5. **Source literals:** a string literal with byte 0 in the source is
   emitted as a sized constant, built once through a runtime helper,
   because a C string literal would end at the NUL.

Functions not listed (dates, numbers and the like) never see NUL bytes in
practice. They keep the `strlen` meaning, and LANGUAGE-GAPS.md lists them
as the last known limit.

## Risks

- **A known-length value passing through an unconverted function loses
  the bytes after its first NUL.** This is no worse than today, which stops
  at the NUL. The probes for each stage catch it in the paths that matter.
- **A buffer changed in place after its length is set.** Only sized
  producers set lengths, and they finish writing first. The debug check
  covers the rest.
- **Performance:** the pointer set is empty unless a program makes a NUL
  byte. `just test` timing is checked after stage 1.
