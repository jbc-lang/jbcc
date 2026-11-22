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
from datetime import date, datetime, timedelta, timezone
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
                                  ('PROGRAM\n', ':1:8:'),
                                  ('PROGRAM one two\n', ':1:13:'),
                                  ('PROGRAM GOTO\nCRT NeverAssigned\n', ':2:5:'),
                                  ('CRT 1 +\n', ':1:8:'),
                                  ('CRT UNKNOWN.FUNCTION(3)\n', ':1:5:'),
                                  ('CRT NUM()\n', ":1:5: wrong argument count for 'NUM'"),
                                  ('CRT NUM(1, 2)\n', ":1:5: wrong argument count for 'NUM'"),
                                  ("CRT ICONV('20121231')\n", ":1:5: wrong argument count for 'ICONV'"),
                                  ("CRT FIELDS('x', ':')\n", ":1:5: wrong argument count for 'FIELDS'"),
                                  ('CRT DATE(1)\n', ':1:5:'),
                                  ('CRT TIME(1)\n', ':1:5:'),
                                  ('CRT TIMEDATE(1)\n', ':1:5:'),
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

    def test_matbuild_diagnostics(self):
        source = self.work / 'matbuild.b'
        source.write_text("MATBUILD Out FROM Missing\n")
        build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn(f"{source}:1:19: expected a dimensioned array 'Missing'", build.stderr)
        for bounds, message in [('', "unassigned element 2 in matrix 'A'"),
                                (', 1, 3', 'MATBUILD position out of bounds'),
                                (', 1.5', 'MATBUILD requires integer positions')]:
            with self.subTest(bounds=bounds):
                source.write_text(f"DIM A(2)\nA(1) = 42\nMATBUILD Out FROM A{bounds}\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:3:1: {message}'.encode(), run.stderr)

    def test_matparse_diagnostics(self):
        source = self.work / 'matparse.b'
        source.write_text('MATPARSE Missing FROM "x"\n')
        build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn(f"{source}:1:10: expected a dimensioned array 'Missing'", build.stderr)
        for bounds, message in [(', 1, 3', 'MATPARSE position out of bounds'),
                                (', 1.5', 'MATPARSE requires integer positions')]:
            with self.subTest(bounds=bounds):
                source.write_text(f'DIM A(2)\nMATPARSE A{bounds} FROM "x"\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:2:1: {message}'.encode(), run.stderr)

    def test_ins_diagnostics(self):
        source = self.work / 'ins.b'
        for program, diagnostic in [
                ("INS 'x' R<1>", ":1:9: expected 'BEFORE'"),
                ("INS 'x' BEFORE R", ':1:17: expected dynamic-array indices'),
                ("INS 'x' BEFORE R<1,1,1,1>", ':1:17: expected one to three dynamic-array indices')]:
            with self.subTest(program=program):
                source.write_text(program + '\n')
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + diagnostic, run.stderr)
        source.write_text("INS 'x' BEFORE R<1,'bad'>\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:16: expected a numeric value'.encode(), run.stderr)

    def test_del_diagnostics(self):
        source = self.work / 'del.b'
        for program, diagnostic in [
                ('DEL R<1>', ":1:5: unassigned variable 'R'"),
                ('R = 1\nDEL R', ':2:6: expected dynamic-array indices'),
                ('R = 1\nDEL R<1,1,1,1>', ':2:6: expected one to three dynamic-array indices')]:
            with self.subTest(program=program):
                source.write_text(program + '\n')
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + diagnostic, run.stderr)
        source.write_text("R = 1\nDEL R<2,'bad'>\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:2:5: DEL requires numeric indices'.encode(), run.stderr)

    def test_exit_status_from_subroutine(self):
        main = self.work / 'main.b'
        sub = self.work / 'finish.b'
        main.write_text("CALL FINISH(20)\nPRINT 'unreachable'\n")
        sub.write_text("SUBROUTINE FINISH(N)\nLOOP\nPRINT 'done'\nEXIT(N + 3.75)\nREPEAT\n")
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 23, run.stderr)
        self.assertEqual(run.stdout, b'done\n')
        sub.write_text("SUBROUTINE FINISH(N)\nEXIT('bad')\n")
        run = self.run_native(main, sub)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{sub}:2:1: expected a numeric value'.encode(), run.stderr)

    def test_exit_control_flow_diagnostics(self):
        source = self.work / 'exit.b'
        source.write_text("LOOP\nIF 1 THEN EXIT\nX = 2\nUNTIL 1 REPEAT\nPRINT X\n")
        build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn(f"{source}:5:7: unknown variable", build.stderr)
        source.write_text("EXIT\nPRINT 'after'\n")
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn(f'{source}:1:1: warning: EXIT outside a loop ignored', build.stderr)
        self.assertEqual(subprocess.check_output([binary]), b'after\n')

    def test_continue_outside_loop(self):
        source = self.work / 'continue.b'
        source.write_text('FOR I = 1 TO 1\nNEXT I\n  CONTINUE\nPRINT I\n')
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn(f'{source}:3:3: warning: CONTINUE outside a loop ignored', build.stderr)
        self.assertEqual(subprocess.check_output([binary]), b'2\n')

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

    def test_locate_subvalue_start_diagnostics(self):
        main = self.work / 'main.b'
        main.write_text("R = 'x'\nLOCATE 'x' IN R<1,1,0> SETTING P ELSE NULL\n")
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{main}:2:1: LOCATE positions start at one'.encode(), run.stderr)
        main.write_text("R = 'x'\nLOCATE 'x' IN R<1,1,1>,2 SETTING P ELSE NULL\n")
        result = subprocess.run([CLI, main, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{main}:2:23: LOCATE with both a subvalue start and a separate start', result.stderr)

    def test_sum_overflow_reports_call_site(self):
        source = self.work / 'sum.b'
        source.write_text("PRINT SUM('9223372036854775807' : @FM : 1)\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:7: integer addition overflow".encode(), run.stderr)

    def test_date_and_time_in_local_timezone(self):
        source = self.work / 'date.b'
        source.write_text("PRINT DATE()\nPRINT OCONV(DATE(),'D-')\nPRINT OCONV(TIME(),'MTS')\n")
        binary = self.work / 'date'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        epoch = date(1967, 12, 31)
        # These fixed offsets span 24 hours, so a UTC-only implementation fails.
        for zone, offset in [('UTC+10', -10), ('UTC-14', 14)]:
            with self.subTest(zone=zone):
                tz = timezone(timedelta(hours=offset))
                before = datetime.now(tz).replace(microsecond=0)
                run = subprocess.run([binary], env=dict(os.environ, TZ=zone),
                                     capture_output=True, text=True, check=True)
                after = datetime.now(tz).replace(microsecond=0)
                count, formatted, clock = run.stdout.splitlines()
                self.assertIn(int(count), [(d.date() - epoch).days for d in (before, after)])
                self.assertIn(formatted, [d.strftime('%m-%d-%Y') for d in (before, after)])
                local_time = datetime.strptime(clock, '%H:%M:%S').time()
                self.assertTrue(any(before <= datetime.combine(d.date(), local_time, tz) <= after
                                    for d in (before, after)))
                self.assertEqual(run.stderr, '')

    def test_timedate_at_local_midnight(self):
        source = self.work / 'timedate.b'
        source.write_text("PRINT TIMEDATE()\nPRINT TIMEDATE()\n")
        subprocess.run([CLI, source, '-o', self.c], check=True)

        # Advance one second per read, starting at 2024-01-01 00:59:59 UTC.
        clock = self.work / 'clock.c'
        clock.write_text("""#include <time.h>
time_t test_clock(time_t *out)
{
    static time_t next = 1704070799;
    time_t now = next++;
    if (out) *out = now;
    return now;
}
""")
        binary = self.work / 'timedate'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-Dtime=test_clock', self.c, clock, '-o', binary], check=True)
        run = subprocess.run([binary], env=dict(os.environ, TZ='UTC+1'), capture_output=True,
                             text=True, check=True)
        self.assertEqual(run.stdout, "23:59:59 31 DEC 2023\n00:00:00 01 JAN 2024\n")
        self.assertEqual(run.stderr, '')

    def test_iconv_diagnostics(self):
        source = self.work / 'date.b'
        cases = [
            ("'20121231', 'MD2'", "unsupported ICONV mask 'MD2'"),
            ("'2012123', 'D'", "ICONV date requires YYYYMMDD"),
            ("'20121231x', 'D'", "ICONV date requires YYYYMMDD"),
            ("'19000229', 'D4'", "invalid ICONV calendar date"),
            ("'20120431', 'D'", "invalid ICONV calendar date"),
            ("'20121301', 'D'", "invalid ICONV calendar date"),
            ("'00000101', 'D'", "invalid ICONV calendar date"),
        ]
        for args, message in cases:
            with self.subTest(args=args):
                source.write_text(f"PRINT ICONV({args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:1:7: {message}".encode(), run.stderr)

    def test_oconv_diagnostics(self):
        source = self.work / 'date.b'
        for args, message in [("0,'MTH'", "unsupported OCONV mask 'MTH'"),
                              ("86400,'MT'", "OCONV time requires whole seconds"),
                              ("0.5,'MTS'", "OCONV time requires whole seconds"),
                              ("-1,'MTS'", "OCONV time requires whole seconds"),
                              ("0,'D5/'", "unsupported OCONV mask 'D5/'"),
                              ("1.5,'D'", "OCONV date requires an integer day count"),
                              ("2933629,'D'", "OCONV date outside years 1 through 9999")]:
            with self.subTest(args=args):
                source.write_text(f"PRINT OCONV({args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:1:7: {message}".encode(), run.stderr)

    def test_trim_diagnostics(self):
        source = self.work / 'trim.b'
        for args, message in [("' ', 'X'", 'unknown TRIM mode'),
                              ("'xx', 'A'", 'TRIM requires a single trim byte')]:
            with self.subTest(args=args):
                source.write_text(f"PRINT TRIM('abc', {args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:1:7: {message}".encode(), run.stderr)

    def test_find_diagnostics(self):
        source = self.work / 'find.b'
        for line, error in [("FIND 'a' IN 'a' SETTING F,V,S,X THEN NULL",
                             "1:30: FIND accepts at most three SETTING variables"),
                            ("FINDSTR 'a' IN 'a' SETTING F,V,S,X THEN NULL",
                             "1:33: FINDSTR accepts at most three SETTING variables"),
                            ("FIND 'a' IN 'a' SETTING F", "1:26: expected THEN or ELSE")]:
            source.write_text(line + '\n')
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f"{source}:{error}", run.stderr)
        for keyword in ('FIND', 'FINDSTR'):
            source.write_text(f"{keyword} 'a' IN 'a',0 SETTING F THEN PRINT F\n")
            run = self.run_native(source)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f"{source}:1:1: {keyword} occurrence must be a positive integer".encode(),
                          run.stderr)

    def test_change_diagnostics(self):
        source = self.work / 'change.b'
        for program, error in [("CHANGE 'x' TO 'y' IN Missing", "1:22: unassigned variable 'Missing'"),
                               ("PRINT CHANGE('a','a')", "1:7: wrong argument count for 'CHANGE'")]:
            source.write_text(program + '\n')
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f"{source}:{error}", run.stderr)
        source.write_text("PRINT CHANGE('x','x','y',1,'bad')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:7: CHANGE requires integer occurrence arguments".encode(), run.stderr)

    def test_abs_diagnostics(self):
        source = self.work / 'abs.b'
        source.write_text("PRINT ABS('text')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:7: ABS requires a numeric value".encode(), run.stderr)
        source.write_text("PRINT ABS(1,2)\n")
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:7: wrong argument count for 'ABS'", run.stderr)

    def test_fmt_diagnostics(self):
        source = self.work / 'fmt.b'
        for mask in ['D4/', 'R20', 'R%', "3'xx'R", 'R2,']:
            with self.subTest(mask=mask):
                source.write_text(f'M = "{mask}"\nPRINT FMT(42,M)\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:2:7: unsupported FMT mask '{mask}'".encode(), run.stderr)

    def test_index_diagnostics(self):
        source = self.work / 'index.b'
        source.write_text("PRINT INDEX('abc', 'b')\n")
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:7: wrong argument count for 'INDEX'", result.stderr)
        source.write_text("PRINT INDEX('abc', 'b', 'two')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:7: expected a numeric value'.encode(), run.stderr)

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

    def test_matrix_parameters(self):
        main = self.work / 'main.b'
        sub = self.work / 'relay.b'
        func = self.work / 'edit.b'
        main.write_text("""N = 2
COMMON /DATA/ Grid(N,3)
DIM Copy(N,3)
MAT Grid = 'seed'
CALL RELAY(MAT Grid, MAT Copy, N, Result)
PRINT Grid(0,0), Grid(2,3), Copy(2,3), Result
""")
        sub.write_text("""SUBROUTINE RELAY(MAT G, MAT D, N, Out)
DIM G(N,3)
DEFFUN EDIT(MAT A, S)
Out = EDIT(MAT G, G(0,0))
MAT D = MAT G
MATBUILD Rec FROM D, 5, 6 USING '|'
Out := Rec
""")
        func.write_text("""FUNCTION EDIT(MAT M, Alias)
FOR I = 1 TO 2
    M(2,3) = Alias : I
NEXT I
Alias = 'new'
RETURN M(2,3)
""")
        run = self.run_native(main, sub, func)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'new\tseed2\tseed2\tseed2seed|seed2\n')

    def test_matrix_parameter_diagnostics(self):
        main = self.work / 'main.b'
        sub = self.work / 'sub.b'
        for call, formal in [('CALL S(MAT A)', 'X'), ('CALL S(N)', 'MAT X')]:
            main.write_text(f'DIM A(2)\n{call}\n')
            sub.write_text(f'SUBROUTINE S({formal})\n')
            result = subprocess.run([CLI, main, sub, '-o', self.c], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(f"{main}:2:6: scalar/MAT argument mismatch for 'S'", result.stderr)
        main.write_text('DIM A(2)\nCALL S(MAT A)\n')
        for body, message in [('DIM X(3)', 'incompatible MAT parameter dimensions'),
                              ('PRINT X(1,1)', 'wrong number of MAT parameter subscripts'),
                              ('PRINT X(3)', 'matrix subscript out of bounds')]:
            sub.write_text(f'SUBROUTINE S(MAT X)\n{body}\n')
            run = self.run_native(main, sub)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f'{sub}:2:'.encode(), run.stderr)
            self.assertIn(message.encode(), run.stderr)

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

    def test_jump_cannot_bypass_for_header(self):
        source = self.work / 'jump.b'
        for jump in ('GOTO', 'GOSUB'):
            with self.subTest(jump=jump):
                source.write_text(f'{jump} middle\nFOR I = 1 TO 2 STEP 1 + 1\nmiddle: PRINT I\nNEXT I\n')
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{source}:1:{len(jump) + 2}: jump to 'middle' would bypass a FOR header",
                              result.stderr)

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

    def test_delete_records(self):
        run = self.run_native(ROOT / 'tests/io/delete.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\ngone\nkeep\nkeep too\nother\nback\n128\n128\n')
        self.assertEqual(run.stderr, b'')

        source = self.work / 'delete.b'
        source.write_text("DELETE 'no default descriptor'\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: DELETE failed'.encode(), run.stderr)

    def test_clearfile(self):
        run = self.run_native(ROOT / 'tests/io/clearfile.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'gone 1\ngone 2\ngone 3\nretained\ndefault cleared\n'
                                     b'reused\nerror 128\n128\nreused\n')
        self.assertEqual(run.stderr, b'')

        source = self.work / 'clearfile.b'
        source.write_text("CLEARFILE\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: CLEARFILE failed'.encode(), run.stderr)

    def test_readv(self):
        run = self.run_native(ROOT / 'tests/io/readv.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'two|values\nlast\nid\nlength 0\nlength 0\n0\n0\n'
                                     b'missing 128 0\ninvalid 128\nfirst status=\ntwo|values\n')
        self.assertEqual(run.stderr, b'')

        source = self.work / 'readv.b'
        source.write_text("READV R FROM 'id','not numeric' ELSE NULL\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: READV requires a numeric field number'.encode(), run.stderr)

    def test_matread(self):
        run = self.run_native(ROOT / 'tests/io/matread.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'6\na\t0\tc\td|e|\n128\ta\te\n1\tshort\t0\n0\t0\n128\tkept\n')
        self.assertEqual(run.stderr, b'')

        source = self.work / 'matread.b'
        source.write_text("MATREAD A FROM 'key' ELSE STOP\n")
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:9: expected a dimensioned array 'A'", run.stderr)
        source.write_text("DIM A(2)\nMATREAD A FROM 'key' LOCKED STOP ELSE STOP\n")
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:2:22: MATREAD LOCKED requires a locking file backend", run.stderr)

    def test_matwrite(self):
        run = self.run_native(ROOT / 'tests/io/matwrite.b',
                              options=['--memory-file', 'EXPLICIT', '--memory-file', 'DEFAULT'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'6\tfirst||left/right|four|five|\n4\n6\tfirst\t0\tright\tfour|five|\n'
                                     b'new\tnew\n128\nnew|new|new|new\n0\n')
        self.assertEqual(run.stderr, b'')
        source = self.work / 'matwrite.b'
        source.write_text("DIM A(2)\nOPEN 'F' TO F ELSE STOP\nA(1) = 42\nMATWRITE A ON F,'id'\n")
        run = self.run_native(source, options=['--memory-file', 'F'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:4:1: unassigned element 2 in matrix 'A'".encode(), run.stderr)

    def test_file_select(self):
        run = self.run_native(ROOT / 'tests/io/select.b', options=['--memory-file', 'F'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'empty\na\t0\t0\na\nc\nd\nc\nd\ndone\nstill done\nc\ncleared\n128\n')
        self.assertEqual(run.stderr, b'')
        source = self.work / 'select.b'
        source.write_text("SELECT TO 11\n")
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:11: select list number must be between 0 and 10", run.stderr)

    def test_clearselect(self):
        run = self.run_native(ROOT / 'tests/io/clearselect.b', options=['--memory-file', 'F'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'default empty\na\n10\nnumbered empty\nb\nnamed empty\n'
                                     b'a\nzero empty\n11\nsecond\n')
        self.assertEqual(run.stderr, b'')
        source = self.work / 'clearselect.b'
        source.write_text("CLEARSELECT 12\n")
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:13: select list number must be between 0 and 11", run.stderr)
        source.write_text("Bad = 'not a list'\nCLEARSELECT Bad\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:2:1: CLEARSELECT requires a select list".encode(), run.stderr)

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

    def test_corpus_matrix_signatures(self):
        (self.work / 'forward').write_text('SUBROUTINE F(MAT A)\nCALL EXT(MAT A)\n'
                                          'IF 0 THEN CALL F(MAT A)\n')
        (self.work / 'mixed').write_text('DIM A(1)\nCALL EXT(MAT A)\nCALL EXT(A(1))\n')
        result = subprocess.run([sys.executable, ROOT / 'tools/check_corpus.py', self.work],
                                capture_output=True, text=True, check=True)
        files = json.loads(result.stdout)['files']
        self.assertEqual(files['forward']['status'], 'translated')
        self.assertIn('mixed:3:6: external calls disagree on signature', files['mixed']['diagnostic'])

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
   X, Y
COMMON Z, Z
COM /EXAMPLE/ X
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

    def test_conflicting_common_declarations(self):
        source = self.work / 'conflict.b'
        for first, second in [('COMMON /X/ A', 'COMMON /Y/ A'),
                              ('COMMON A', 'COMMON /X/ A'),
                              ('COMMON /X/ A(2)', 'COMMON /X/ A'),
                              ('COMMON /X/ A', 'COMMON /X/ A(2)')]:
            with self.subTest(first=first, second=second):
                source.write_text(f'{first}\n{second}\n')
                run = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:2:12: duplicate declaration of 'A'", run.stderr)

    def test_runtime_common_dimensions(self):
        main = self.work / 'main.b'
        sub = self.work / 'change.b'
        main.write_text("""CFG<1> = 2
COMMON /CACHE/ Head, Rows(CFG<1>, 1), Tail, More(CFG<1> + 1)
CFG<1> = 8
Head = 'head'
Tail = 'tail'
MAT Rows = 'row'
Rows(2,1) = 'edge'
MAT More = 'extra'
CALL CHANGE()
PRINT Head, Rows(0,0), Rows(2,1), Tail, More(3)
""")
        sub.write_text("""SUBROUTINE CHANGE()
N = 1
COMMON /CACHE/ H, M(2,N), T, X(3)
DIM Copy(2,1)
MAT Copy = MAT M
MAT Copy = Copy(2,1) : '!'
MAT M = MAT Copy
T := '!'
X(3) := '!'
""")
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'head\tedge!\tedge!\ttail!\textra!\n')

    def test_local_dimensions_per_invocation(self):
        main = self.work / 'main.b'
        routine = self.work / 'nested.b'
        bump = self.work / 'bump.b'
        main.write_text('CALL NESTED(2)\n')
        routine.write_text("""SUBROUTINE NESTED(N)
DEFFUN BUMP(X)
X = 0
DIM Grid(BUMP(X), BUMP(X) + N)
Grid(1,2+N) = N
IF N > 0 THEN CALL NESTED(N-1)
PRINT X, Grid(1,2+N)
""")
        bump.write_text('FUNCTION BUMP(X)\nX += 1\nRETURN X\n')
        run = self.run_native(main, routine, bump)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'2\t0\n2\t1\n2\t2\n')

    def test_local_dimension_errors(self):
        source = self.work / 'bad.b'
        cases = [
            ("N = 1.5\nDIM A(N)", ':2:7: expected a positive integer dimension'),
            ("N = 50000\nDIM A(N,N)", ':2:5: dimensioned array is too large'),
            ("N = 2\nIF 0 THEN DIM A(N)\nMAT A = 0", ':3:5: local matrix declaration has not executed'),
            ("FOR N = 1 TO 2\nDIM A(N)\nNEXT", ':2:5: incompatible local matrix dimensions'),
            ("N = 2\nDIM A(N)\nN = 3\nA(N) = 1", ':4:1: matrix subscript out of bounds'),
        ]
        for program, location in cases:
            with self.subTest(program=program):
                source.write_text(program)
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + location).encode(), run.stderr)

    def test_runtime_common_dimension_errors(self):
        source = self.work / 'bad.b'
        cases = [
            ("N = 1.5\nCOMMON A(N)", ':2:10: expected a positive integer dimension'),
            ("N = 50000\nCOMMON A(N,N)", ':2:8: dimensioned array is too large'),
            ("N = 2\nIF 0 THEN COMMON A(N)\nMAT A = 0", ':3:5: COMMON matrix declaration has not executed'),
            ("N = 2\nCOMMON A(N,1), B(1,N)\nMAT B = 0\nMAT A = MAT B", ':4:13: incompatible MAT copy dimensions'),
            ("FOR N = 1 TO 2\nCOMMON A(N)\nNEXT", ':2:8: incompatible COMMON matrix dimensions'),
        ]
        for program, location in cases:
            with self.subTest(program=program):
                source.write_text(program)
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + location).encode(), run.stderr)

    def test_common_runtime_shape_across_routines(self):
        main = self.work / 'main.b'
        sub = self.work / 'sub.b'
        main.write_text('N = 2\nCOMMON /X/ A(N,N-1)\nCALL DIFFERENT()\n')
        sub.write_text('SUBROUTINE DIFFERENT()\nCOMMON /X/ B(1,2)\n')
        run = self.run_native(main, sub)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{sub}:2:12: incompatible COMMON matrix dimensions'.encode(), run.stderr)

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
