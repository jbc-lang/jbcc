import json
import math
import re
import select
import os
import shlex
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'jbcc'


class CompilerTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.work = Path(tmp.name)
        self.c = self.work / 'generated.c'

    def run_native(self, *sources, options=()):
        subprocess.run([CLI, *options, *sources, '-o', self.c], check=True)
        binary = self.work / 'program'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-pedantic', self.c, '-o', binary], check=True)
        return subprocess.run([binary], capture_output=True, timeout=5)

    def test_snippets(self):
        for source in sorted((ROOT / 'tests/snippets').glob('*.b')):
            with self.subTest(source=source.name):
                run = self.run_native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, source.with_suffix('.stdout').read_bytes())
                self.assertEqual(run.stderr, b'')

    def test_diagnostics_preserve_existing_output(self):
        source = self.work / 'invalid.b'
        for program, location in [('N = 2\nIF N THEN\n', ':2:1:'),
                                  ('CRT 1 +\n', ':1:8:'),
                                  ('CRT ABS(3)\n', ':1:5:'),
                                  ('FOR I = 1 TO 2\nNEXT J\n', ':2:6:'),
                                  ('LOOP WHILE 0\n', ':1:1:'),
                                  ('IF 0 THEN X = 1\nCRT X\n', ':2:5:')]:
            with self.subTest(program=program):
                source.write_text(program)
                self.c.write_text('previous output')
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + location, run.stderr)
                self.assertEqual(self.c.read_text(), 'previous output')

    def test_integer_limits(self):
        source = self.work / 'numbers.b'
        for text, diagnostic in [('9223372036854775807', 'overflow'),
                                 ('"nan"', 'requires numeric operands')]:
            with self.subTest(text=text):
                source.write_text(f'CRT {text} + 1\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(diagnostic.encode(), run.stderr)
                self.assertIn(f'{source}:1:{len(text) + 6}:'.encode(), run.stderr)

    def test_logical_function_calls(self):
        main = self.work / 'main.b'
        function = self.work / 'BUMP'
        function.write_text('FUNCTION BUMP(N)\nN += 1\nRETURN(N)\n')
        main.write_text('DEFFUN BUMP()\nN = 0\n'
                        'PRINT 1 OR BUMP(N), 0 AND BUMP(N), N\n'
                        'PRINT 0 OR BUMP(N), 1 AND BUMP(N), N\n'
                        'PRINT BUMP(N) OR BUMP(N), N\n')
        run = self.run_native(main, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'1\t0\t0\n1\t1\t2\n1\t3\n')
        main.write_text('DEFFUN BUMP()\nPRINT 1 OR BUMP(X)\nPRINT X\n')
        run = subprocess.run([CLI, main, function, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{main}:3:7: unknown variable', run.stderr)

    def test_precision_call_scope(self):
        main = self.work / 'main.b'
        function = self.work / 'LOCAL'
        sub = self.work / 'CHANGE'
        main.write_text('DEFFUN LOCAL()\nPRECISION 2\nCALL CHANGE()\n'
                        'PRINT LOCAL()\nPRINT 2 / 3\n')
        sub.write_text('SUBROUTINE CHANGE()\nPRINT 2 / 3\nPRECISION 4\nPRINT 2 / 3\n')
        function.write_text('FUNCTION LOCAL()\nPRECISION 3\nRETURN(2 / 3)\n')
        run = self.run_native(main, sub, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0.66\n0.6666\n0.666\n0.66\n')

    def test_invalid_precision(self):
        source = self.work / 'bad.b'
        for value in ('-1', '2.5', '"text"', '2147483648'):
            with self.subTest(value=value):
                source.write_text(f'P = {value}\nPRECISION P\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:2:1: PRECISION'.encode(), run.stderr)

    def test_locate_diagnostics(self):
        main = self.work / 'main.b'
        for clause, message in [("BY 'XX'", 'unsupported LOCATE order'),
                                (',0', 'LOCATE positions start at one'),
                                (',1.5', 'LOCATE start must be a positive integer')]:
            with self.subTest(clause=clause):
                main.write_text(f"LOCATE 'x' IN 'x' {clause} SETTING P ELSE NULL\n")
                run = self.run_native(main)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{main}:1:1: {message}'.encode(), run.stderr)

    def test_division_by_zero(self):
        source = self.work / 'division.b'
        source.write_text('PRINT 7 / 0\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:9: division by zero'.encode(), run.stderr)

    def test_external_subroutine(self):
        directory = ROOT / 'tests/routines'
        run = self.run_native(directory / 'caller.b', directory / 'get.status.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'open\nclosed\n')

    def test_insert_locations(self):
        source = self.work / 'main.b'
        header = self.work / 'I_BROKEN'
        source.write_text('$INSERT I_BROKEN\n')
        for content, location in [('CRT 1 +\n', ':1:8:'), ('$INSERT I_BROKEN\n', ':1:1:')]:
            header.write_text(content)
            run = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(str(header) + location, run.stderr)
        header.write_text('EQU BAD TO 1 / 0\n')
        source.write_text('$INSERT I_BROKEN\nPRINT BAD\n')
        run = self.run_native(source)
        self.assertIn(f'{header}:1:14: division by zero'.encode(), run.stderr)

    def test_call_aliases_and_expression_arguments(self):
        caller = self.work / 'caller.b'
        callee = self.work / 'callee.b'
        caller.write_text('X = 1\nCALL TWICE(X, X)\nCALL TWICE(X + 1, X)\nPRINT X\n')
        callee.write_text('SUBROUTINE TWICE(A, B)\nA += 1\nB += A\nRETURN\n')
        run = self.run_native(callee, caller)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'10\n')

    def test_external_function(self):
        directory = ROOT / 'tests/routines'
        binary = self.work / 'program'
        subprocess.run([CLI, '--exe', directory / 'function.caller.b',
                        directory / 'DOUBLE.IT', '-o', binary], check=True)
        self.assertEqual(subprocess.check_output([binary]), b'43\n')

    def test_function_arguments_and_returns(self):
        main = self.work / 'main.b'
        inc = self.work / 'INC'
        empty = self.work / 'EMPTY'
        main.write_text("""DEFFUN INC(N)
DEFFUN EMPTY()
DEFFUN UNUSED()
DIM M(1)
M(0) = 2
PRINT M(0) : INC(M(0)) : M(0)
PRINT INC(INC(M(0))) : M(0)
PRINT '[' : EMPTY() : ']'
""")
        inc.write_text('FUNCTION INC(N)\nGOSUB increment\nGOSUB finish\nRETURN 99\n'
                       'increment: N += 1\nRETURN\nfinish: RETURN N\n')
        empty.write_text('FUNCTION EMPTY()\nRETURN\n')
        run = self.run_native(empty, inc, main)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'233\n54\n[]\n')

    def test_function_diagnostics(self):
        main = self.work / 'main.b'
        definition = ROOT / 'tests/routines/DOUBLE.IT'
        for text, message in [('DEFFUN MISSING()\nCRT MISSING()', ":2:5: unknown function 'MISSING'"),
                              ('DEFFUN DOUBLE.IT()\nCRT DOUBLE.IT()', ":2:5: wrong argument count"),
                              ('CRT DOUBLE.IT(1)\nDEFFUN DOUBLE.IT()', ':1:5: unknown variable'),
                              ('CALL DOUBLE.IT(1)', ":1:6: unknown subroutine")]:
            with self.subTest(text=text):
                main.write_text(text)
                run = subprocess.run([CLI, main, definition, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(main) + message, run.stderr)

    def test_bad_routine_references(self):
        main = self.work / 'main.b'
        sub = self.work / 'sub.b'
        sub.write_text('SUBROUTINE CHECK(X)\nRETURN\n')
        for program, message in [('CALL CHECK()', 'wrong argument count'),
                                 ('CALL MISSING()', 'unknown subroutine'),
                                 ('GOSUB missing', 'unknown label'),
                                 ('here:\nhere:', 'duplicate label')]:
            with self.subTest(program=program):
                main.write_text(program)
                run = subprocess.run([CLI, main, sub, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message, run.stderr)

    def test_memory_files(self):
        run = self.run_native(ROOT / 'tests/io/records.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'missing file\nwrite failed\nmissing record\nsaved1\nsaved2\n'
                                     b'record2\nempty=0\nrecord2\n')

    def test_corpus_report(self):
        (self.work / 'ok').write_text('SUBROUTINE S(X)\nDEFFUN F()\nCALL OTHER(X)\n'
                                      'X = F(X)\nIF X THEN CALL S(X)\n')
        (self.work / 'bad').write_text('MAT A = 2\n')
        (self.work / 'I_SHARED').write_text('EQU X TO 1\n')
        report = subprocess.run([sys.executable, ROOT / 'tools/check_corpus.py', self.work],
                                capture_output=True, text=True, check=True)
        data = json.loads(report.stdout)
        self.assertEqual(data['counts'], {'translated': 1, 'rejected': 1, 'include fragment': 1})
        self.assertEqual(data['files']['ok']['status'], 'translated')
        self.assertEqual(data['first_blockers'], {"expected a dimensioned array 'A'": 1})
        self.assertIn('bad:1:5:', data['files']['bad']['diagnostic'])

    def test_quine(self):
        source = ROOT / 'tests/programs/quine.b'
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, source.read_bytes())

    def test_char_byte_range(self):
        source = self.work / 'char.b'
        source.write_text('CRT CHAR(1) : CHAR(254) : CHAR("255.0"):\n')
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, bytes([1, 254, 255]))
        for value, message in [('0', 'embedded NUL'), ('256', '0 to 255'), ('1.5', '0 to 255')]:
            with self.subTest(value=value):
                source.write_text(f'CRT CHAR({value})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message.encode(), run.stderr)
                self.assertIn(f'{source}:1:5:'.encode(), run.stderr)

    def test_common_storage(self):
        caller = self.work / 'caller.b'
        sub = self.work / 'sub.b'
        caller.write_text("""COM /EXAMPLE/ X, A(2),
   Y
COMMON Z
X = 'caller'
A(2) = 'matrix'
FOR I = 1 TO 2
  CALL CHANGE(I)
NEXT
PRINT X, A(2), Y, Z
""")
        sub.write_text("""SUBROUTINE CHANGE(I)
COMMON /EXAMPLE/ P, M(2), Q
COMMON Unnamed
P = P : I
M(2) = M(2) : I
Q = M(2)
Unnamed = 'ok' : I
RETURN
""")
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'caller12\tmatrix12\tmatrix12\tok2\n')
        sub.write_text('SUBROUTINE CHANGE(I)\nCOM /EXAMPLE/ P, M(3), Q\n')
        result = subprocess.run([CLI, caller, sub, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('incompatible COMMON layout', result.stderr)

    def test_executable_mode(self):
        binary = self.work / 'output with spaces'
        cmd = [CLI, '--exe', ROOT / 'tests/snippets/coercion.b', '-o', binary]
        env = os.environ.copy()
        env.pop('CC', None)
        env.pop('CC_FLAGS', None)
        subprocess.run(cmd, env=env, check=True)
        expected = binary.read_bytes()
        self.assertEqual(subprocess.check_output([binary]), b'5\n23\n')

        wrapper = self.work / 'check flags.py'
        wrapper.write_text("import sys\nassert '--argument with spaces' in sys.argv\nsys.exit(42)\n")
        env.update(CC=shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper)),
                   CC_FLAGS="'--argument with spaces'")
        run = subprocess.run(cmd, env=env, text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn('status 42', run.stderr)
        self.assertEqual(binary.read_bytes(), expected)

    def test_assignment_predicates_on_arguments(self):
        caller = self.work / 'caller.b'
        sub = self.work / 'init.b'
        caller.write_text('CALL INIT(X)\nCALL INIT(X)\nPRINT LEN(X)\n')
        sub.write_text("SUBROUTINE INIT(P)\nPRINT ASSIGNED(P)\nIF UNASSIGNED(P) THEN P = ''\n")
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\n1\n0\n')

    def test_assignment_probe_does_not_initialize(self):
        source = self.work / 'probe.b'
        for program, location in [('PRINT ASSIGNED(X)\nPRINT X', ':2:7:'),
                                  ('PRINT ASSIGNED(2)', ':1:16:'),
                                  ('PRINT UNASSIGNED(X + 1)', ':1:20:')]:
            with self.subTest(program=program):
                source.write_text(program)
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(source) + location, result.stderr)

    def test_remove_shared_cursor(self):
        caller = self.work / 'caller.b'
        sub = self.work / 'take.b'
        caller.write_text("""COMMON /R/ List
List = 'first' : @AM : 'last'
CALL TAKE(List, Part)
PRINT Part
REMOVE Part FROM List SETTING D
PRINT Part, D
CALL TAKE(List, Part)
PRINT Part
""")
        sub.write_text("""SUBROUTINE TAKE(Arg, Out)
COMMON /R/ Shared
REMOVE Out FROM Arg SETTING D
IF D EQ 0 THEN
  Shared = Shared
  REMOVE Out FROM Arg SETTING D
END
""")
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'first\nlast\t0\nfirst\n')

    def test_matrix_assignment_diagnostics(self):
        source = self.work / 'main.b'
        source.write_text('DIM A(2), B(2)\nB(0) = 0\nMAT A = MAT B\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:3:13: unassigned element in matrix 'B'".encode(), run.stderr)
        source.write_text('DIM A(2,1), B(1,2)\nMAT A = MAT B\n')
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:2:13: MAT copy between different dimensions', run.stderr)

    def test_matrix_fill_evaluates_expression_once(self):
        source = self.work / 'main.b'
        function = self.work / 'BUMP'
        source.write_text('DIM A(2)\nDEFFUN BUMP()\nN = 0\nMAT A = BUMP(N)\n'
                          'PRINT N, A(0), A(1), A(2)\n')
        function.write_text('FUNCTION BUMP(N)\nN += 1\nRETURN N\n')
        run = self.run_native(source, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'1\t1\t1\t1\n')

    def test_matrix_element_argument_and_bounds(self):
        main = self.work / 'main.b'
        callee = self.work / 'put.b'
        main.write_text('DIM A(2)\nCALL PUT(A(0))\nPRINT A(0)\n')
        callee.write_text('SUBROUTINE PUT(X)\nX = 7\n')
        run = self.run_native(main, callee)
        self.assertEqual(run.stdout, b'7\n')
        main.write_text('DIM A(2)\nA(3) = 7\n')
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{main}:2:1: matrix subscript out of bounds'.encode(), run.stderr)

    def test_banner(self):
        source = ROOT / 'tests/programs/banner.b'
        binary = self.work / 'banner'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        home = b'\x1b[H\n'
        blank = home + (b' ' * 79 + b'\n') * 24
        with subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as process:
            try:
                frames = bytearray()
                while len(frames) < 2 * len(blank):
                    self.assertTrue(select.select([process.stdout], [], [], 5)[0], 'frame timeout')
                    chunk = os.read(process.stdout.fileno(), 4096)
                    self.assertTrue(chunk, 'banner exited before second frame')
                    frames.extend(chunk)
                _, err = process.communicate(input=b'q', timeout=5)
                self.assertEqual(process.returncode, 0, err)
            finally:
                process.kill()
        self.assertEqual(frames[:len(blank)], blank)
        # Project the fixture's artwork independently at time zero.
        art = re.findall(r'^M\( *\d+\) = "([ X]+)"', source.read_text(), re.M)
        expected = bytearray(home)
        for row in range(24):
            y = 2 * row / 24 - 1
            for col in range(79):
                x = 2 * (col - 39.5) / 79
                scale = 2 / (1 + .08 * (math.sin(math.tau * (1 + x)) + math.cos(math.tau * y)))
                u = 39.5 + int(.6 * x * scale * 39.5)
                v = 12 + int(.6 * y * scale * 12)
                pixel = art[v][int(u)] if 0 <= u < 79 and 0 <= v < 24 else ' '
                expected.append(ord(pixel))
            expected.append(10)
        self.assertEqual(frames[len(blank):2 * len(blank)], expected)

    def test_system14_input_queue(self):
        source = self.work / 'pending.b'
        source.write_text('PRINT SYSTEM(14)\nPRINT SYSTEM(14)\n')
        binary = self.work / 'pending'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        with open(os.devnull, 'rb') as empty:
            self.assertEqual(subprocess.check_output([binary], stdin=empty), b'0\n0\n')
        # Preload the pipe before starting the program. Polling leaves its bytes queued.
        read_fd, write_fd = os.pipe()
        with os.fdopen(write_fd, 'wb') as writer:
            writer.write(b'abc')
        with os.fdopen(read_fd, 'rb') as reader:
            self.assertEqual(subprocess.check_output([binary], stdin=reader), b'3\n3\n')
