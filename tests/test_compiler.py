import subprocess
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
