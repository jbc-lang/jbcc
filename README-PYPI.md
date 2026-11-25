# jbcc

jbcc is an experimental compiler for jBC, the MultiValue BASIC dialect used
in jBASE and Temenos T24. It translates jBC to standalone C99.

Try jBC in your browser at the [jBC Playground](https://online.jbc-lang.org/).

```sh
printf '%s\n' 'CRT "Hello, jBC!"' > hello.b
uvx jbcc hello.b -o hello.c
uvx jbcc --run hello.b
```

Native builds with `--exe` or `--run` need a C99 compiler on PATH. jbcc uses
`cc` by default. Set `CC` and `CC_FLAGS` to override the compiler and flags.

The parser has been tested against T24 R07 and R10 sources. Parts of the
jBASE runtime are still to be implemented.

- [Compiler source and examples](https://github.com/jbc-lang/jbcc)
- [jBC language guide](https://jbc-lang.org/)
- [MIT license for the original code](https://github.com/jbc-lang/jbcc/blob/main/LICENSE)
- [Unicode notice for the CP037 tables](https://github.com/jbc-lang/jbcc/blob/main/THIRD-PARTY-NOTICES.md)
