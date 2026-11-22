# jbcc

jbcc is a jBC-to-C compiler project. Its first target is a native executable
built with the system C compiler. The project is at the design stage.

## First executable milestone

Translate this complete jBC program to readable C, compile the C, and run it:

```basic
N = "2"
CRT N + 3
CRT N : 3
```

The proposed stdout is `5\n23\n`. This is a provisional test expectation.
It exercises the distinction between numeric addition and string
concatenation on the same variable. The initial subset needs literals,
scalar assignment, these two binary operators and line-oriented CRT output.

The planned command is `jbcc sample.b -o sample.c`. A small C runtime will
own jBC value conversion and printing. The translator will report unsupported
syntax with a source location. Calls to unimplemented services should identify
the service and call site. Later snippets can supply explicit test
implementations for services such as record I/O.

## Evidence for the implementation

The [grammar investigation](https://github.com/jbc-lang/jbc-language/pull/11)
contains two token grammars, a lexer keyword table and a function catalogue.
The preprocessor handles includes, equates and macros. The main parser handles
statements and expressions. Some scanner decisions depend on declarations or
parser state, so the grammar alone cannot tokenize raw source.

Use the [Programmers Reference Guide](https://jbc-lang.org/) for documented
syntax, output examples and dialect notes. Record the source of each test
expectation. A locally available T24 corpus can tell us which constructs
occur together and how often. Executable snippets with independently checked
output are the evidence for runtime behavior.

## After the first milestone

Add conditionals and dynamic-array extraction and replacement. Once native
execution is repeatable, evaluate compiling the same generated C and runtime
to WebAssembly for a browser playground.
