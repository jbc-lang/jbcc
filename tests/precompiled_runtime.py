"""Prepare a reusable object for native tests that use the default runtime."""

import json
import re
import subprocess
from pathlib import Path

from compiler_support import C_FLAGS, ROOT

RUNTIME_SOURCE = ROOT / 'src/jbcc/jbc.c'
HEADER = 'jbcc-test-runtime.h'
OBJECT = 'jbcc-test-runtime.o'
STATIC = b'static '
RUNTIME_MACROS = re.compile(
    rb'^#define (?:jbc_run_exit_callbacks|jbc_terminate|'
    rb'JBC_SCREEN|jbc_print_channel|jbc_output)\b[^\n]*',
    re.MULTILINE,
)


def _token_end(location):
    return location['offset'] + location['tokLen']


def _runtime_interface(source, declarations, compiler_names):
    preamble, _ = source.split(b'\nstruct jbc_buffer {', 1)
    header = [preamble]
    exports = set()
    for declaration in declarations:
        location = declaration.get('loc', {})
        if 'includedFrom' in location or 'offset' not in location:
            continue

        begin = declaration['range']['begin']
        end = declaration['range']['end']
        if 'offset' not in begin or 'offset' not in end:
            continue
        start = begin['offset']
        kind = declaration['kind']
        name = declaration.get('name', '').encode()
        private = declaration.get('storageClass') == 'static'
        if private and name not in compiler_names:
            continue
        if kind == 'FunctionDecl':
            stop = _token_end(end)
            for child in declaration.get('inner', ()):
                if child['kind'] == 'CompoundStmt':
                    stop = child['range']['begin']['offset']
                    break
            signature = source[start:stop].rstrip()
            header.append(signature.removeprefix(STATIC) + b';')
        elif kind == 'VarDecl' and name in compiler_names:
            c_type = declaration['type']['qualType'].encode()
            base, bracket, dimensions = c_type.partition(b'[')
            header.append(
                b'extern '
                + base.rstrip()
                + b' '
                + name
                + bracket
                + dimensions
                + b';'
            )
        elif kind in ('TypedefDecl', 'EnumDecl') or (
            kind == 'RecordDecl'
            and name
            and declaration.get('completeDefinition')
        ):
            header.append(source[start : _token_end(end)] + b';')
        else:
            continue
        if private:
            exports.add(start)
    header.extend(RUNTIME_MACROS.findall(source))
    return b'\n'.join(dict.fromkeys(header)) + b'\n', exports


def prepare_runtime(directory):
    """Return False when cc has no Clang AST support."""
    version = subprocess.check_output(['cc', '--version'])
    if b'clang' not in version.lower():
        return False

    tree = subprocess.check_output(
        [
            'cc',
            *C_FLAGS,
            '-fsyntax-only',
            '-Xclang',
            '-ast-dump=json',
            RUNTIME_SOURCE,
        ]
    )
    source = RUNTIME_SOURCE.read_bytes()
    # Generated C refers to some private runtime names. Export those for the
    # test object while leaving the checked-in C source untouched.
    compiler_source = (ROOT / 'src/jbcc/compiler.py').read_bytes()
    compiler_names = set(re.findall(rb'\b[A-Za-z_]\w*\b', compiler_source))
    header, exports = _runtime_interface(
        source, json.loads(tree)['inner'], compiler_names
    )
    (directory / HEADER).write_bytes(header)
    for start in sorted(exports, reverse=True):
        assert source[start : start + len(STATIC)] == STATIC
        source = source[:start] + source[start + len(STATIC) :]
    implementation = directory / 'jbcc-test-runtime.c'
    implementation.write_bytes(source)
    subprocess.run(
        ['cc', *C_FLAGS, '-c', implementation, '-o', directory / OBJECT],
        check=True,
    )
    return True


class PrecompiledRuntime:
    def __init__(self, directory):
        self.directory = Path(directory)
        self.source = RUNTIME_SOURCE.read_bytes()

    def compiler_inputs(self, standalone):
        features, found, program = standalone.read_bytes().partition(
            self.source
        )
        if not found or features.strip():
            return [standalone]
        thin = standalone.with_name('program.c')
        thin.write_bytes(b'#include "' + HEADER.encode() + b'"\n' + program)
        return ['-I', self.directory, thin, self.directory / OBJECT]
