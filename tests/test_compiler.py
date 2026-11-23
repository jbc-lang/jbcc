import fcntl
import json
import math
import re
import select
import os
import pwd
import shlex
import struct
import subprocess
import sys
import tempfile
import termios
import time
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

    def run_native(self, *sources, options=(), env=None, cwd=None):
        subprocess.run([CLI, *options, *sources, '-o', self.c], check=True)
        binary = self.work / 'program'
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror',
                        '-pedantic', self.c, '-lm', '-o', binary], check=True)
        return subprocess.run([binary], capture_output=True, timeout=5, env=env, cwd=cwd)

    def test_snippets(self):
        for source in sorted((ROOT / 'tests/snippets').glob('*.b')):
            with self.subTest(source=source.name):
                run = self.run_native(source)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, source.with_suffix('.stdout').read_bytes())
                self.assertEqual(run.stderr, b'')

    def test_heading_automatic_page_break(self):
        source = self.work / 'pages.b'
        source.write_text("""HEADING "Page ^'N'"
FOR I = 1 TO 24
    PRINT I
NEXT I
""")
        result = self.run_native(source)
        body = b''.join(f"{i}\n".encode() for i in range(1, 24))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b"Page 1\n" + body + b"\fPage 2\n24\n")

    def test_heading_terminal_pause(self):
        source = self.work / 'report.b'
        source.write_text("""HEADING 'First'
HEADING "Second'N'"
PAGE
CRT 'done'
""")
        binary = self.work / 'report'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        with subprocess.Popen([binary], stdin=slave, stdout=slave) as proc:
            try:
                output = bytearray()
                while not output.endswith(b'First\r\n'):
                    self.assertTrue(select.select([master], [], [], 5)[0], output)
                    output.extend(os.read(master, 1024))
                self.assertFalse(select.select([master], [], [], 0.1)[0])
                os.write(master, b'\n')
                self.assertEqual(proc.wait(timeout=5), 0)
                while not output.endswith(b'done\r\n'):
                    self.assertTrue(select.select([master], [], [], 5)[0], output)
                    output.extend(os.read(master, 1024))
                self.assertIn(b'\fSecond\r\n\fSecond\r\ndone\r\n', output)
            finally:
                proc.kill()

    def test_lptrhigh_tracks_current_print_destination(self):
        source = self.work / 'height.b'
        source.write_text("""CRT @LPTRHIGH
PRINTER ON ON 7
CRT @LPTRHIGH
PRINT @LPTRHIGH
PRINTER OFF
CRT @LPTRHIGH
""")
        binary = self.work / 'height'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        env = dict(os.environ, JBCC_PRINT_DIR=str(self.work))

        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 42, 80, 0, 0))
        mode = termios.tcgetattr(slave)
        mode[1] &= ~termios.OPOST
        termios.tcsetattr(slave, termios.TCSANOW, mode)
        run = subprocess.run([binary], env=env, stdout=slave, stderr=subprocess.PIPE, timeout=5)
        self.assertEqual((run.returncode, run.stderr), (0, b''))
        expected = b'42\n24\n42\n'
        output = bytearray()
        while len(output) < len(expected):
            self.assertTrue(select.select([master], [], [], 5)[0], output)
            output.extend(os.read(master, 1024))
        self.assertEqual(output, expected)

        run = subprocess.run([binary], env=env, capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, b'24\n24\n24\n', b''))
        self.assertEqual([job.read_bytes() for job in self.work.glob('unit-7-*')], [b'24\n'] * 2)

    def test_footing_reserves_rows_and_closes_printer_page(self):
        source = self.work / 'footing.b'
        source.write_text("""HEADING 'Start ^'
FOOTING "End ^'L'Last"
FOR I = 1 TO 22
    PRINT I
NEXT I
PAGE 9
FOOTING ''
PRINTER ON
FOOTING ON 2 'Job ^^'
PRINT ON 2 'body'
CRT 'screen'
PRINTER CLOSE ON 2
""")
        run = self.run_native(source, env=dict(os.environ, JBCC_PRINT_DIR=str(self.work)))
        self.assertEqual(run.returncode, 0, run.stderr)
        first_page = b'Start 1\n' + b''.join(f'{i}\n'.encode() for i in range(1, 22))
        self.assertEqual(run.stdout, first_page + b'End 1\nLast\n\fStart 2\n22\n' +
                         b'\n' * 20 + b'End 2\nLast\n\fStart 9\nscreen\n')
        job, = self.work.glob('unit-2-*')
        self.assertEqual(job.read_bytes(), b'body\n' + b'\n' * 22 + b'Job    1\n')
        self.assertEqual(run.stderr, b'')

    def test_footing_terminal_pause_and_no_pause(self):
        source = self.work / 'footing.b'
        source.write_text("""FOOTING 'End ^'
PRINT 'first'
PAGE
FOOTING "End ^'N'"
PRINT 'second'
PAGE
PRINT 'third':
""")
        binary = self.work / 'footing'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        with subprocess.Popen([binary], stdin=slave, stdout=slave) as proc:
            try:
                first = bytearray()
                while not first.endswith(b'End 1\r\n'):
                    self.assertTrue(select.select([master], [], [], 5)[0], first)
                    first.extend(os.read(master, 1024))
                self.assertEqual(first, b'first\r\n' + b'\r\n' * 22 + b'End 1\r\n')
                self.assertFalse(select.select([master], [], [], 0.1)[0])
                os.write(master, b'\n')
                self.assertEqual(proc.wait(timeout=5), 0)
                rest = bytearray()
                while not rest.endswith(b'End 3\r\n'):
                    self.assertTrue(select.select([master], [], [], 5)[0], rest)
                    rest.extend(os.read(master, 1024))
                self.assertIn(b'\fsecond\r\n' + b'\r\n' * 22 + b'End 2\r\n', rest)
                self.assertTrue(rest.endswith(b'\fthird\r\n' + b'\r\n' * 22 + b'End 3\r\n'))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_sequential_block_io(self):
        (self.work / 'input').write_bytes(b'a\r\n\xfeend')
        (self.work / 'binary').write_bytes(b'x\0yz')
        result = self.run_native(ROOT / 'tests/io/block-io.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'aRN|\t0\nen\nshort\t128\t0\nd\neof\t128\n'
                                        b'readonly\t24576\npending\t128\nwrote\t0\nA\nB\n'
                                        b'nul\t32768\t0\nz\n')
        self.assertEqual((self.work / 'output').read_bytes(), b'AXB')
        self.assertEqual((self.work / 'input').read_bytes(), b'a\r\n\xfeend')

    def test_block_io_operand_diagnostics(self):
        source = self.work / 'invalid.b'
        for statement, message in [
            ("READBLK V FROM '',2 ELSE NULL", 'READBLK requires nonempty handle and block size'),
            ("READBLK V FROM 'file',0 ELSE NULL", 'READBLK requires a positive integer block size'),
            ("READBLK V FROM 'file',1.5 ELSE NULL", 'READBLK requires a positive integer block size'),
            ("WRITEBLK '' TO 'file' ELSE NULL", 'WRITEBLK requires nonempty handle and data'),
        ]:
            with self.subTest(statement=statement):
                source.write_text(statement + '\n')
                result = self.run_native(source, cwd=self.work)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:1:1: {message}'.encode(), result.stderr)

    def test_sequential_create_and_truncate(self):
        (self.work / 'zero').write_bytes(b'old content')
        (self.work / 'input').write_bytes(b'keep\n' + b'discard\n' * 2000)
        result = self.run_native(ROOT / 'tests/io/seq-create.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'created 0\nempty\nlost race\n32768\nexists\n'
                         b'keep 0\nend\nreadonly 24576\ndenied\ndone\n')
        self.assertEqual((self.work / 'new').read_bytes(), b'winner\n')
        self.assertEqual((self.work / 'input').read_bytes(), b'keep\nreplacement\n')
        self.assertEqual((self.work / 'empty').read_bytes(), b'')
        self.assertEqual((self.work / 'zero').read_bytes(), b'')

    def test_create_null_handle(self):
        source = self.work / 'null.b'
        source.write_text("F = ''\nCREATE F ELSE CRT 'failed'\n")
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:2:1: CREATE requires an OPENSEQ handle'.encode(), result.stderr)

    def test_flush_sequential_file(self):
        source = self.work / 'flush.b'
        source.write_text("""OPENSEQ 'report' TO F THEN STOP
FLUSH F SETTING S THEN STOP ELSE CRT S:':':STATUS()
EXECUTE 'test ! -e report' RETURNING Check
CRT Check
WRITESEQ 'visible' TO F ELSE STOP
FLUSH F SETTING S THEN CRT S:':':STATUS() ELSE STOP
FLUSH F
EXECUTE 'cat report'
CLOSESEQ F
""")
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'128:128\n0\n0:0\nvisible\n')
        self.assertEqual(result.stderr, b'')

    def test_nobuf_uses_unbuffered_sequential_io(self):
        data = self.work / 'data'
        data.write_bytes(b'first\nold\n')
        source = self.work / 'nobuf.b'
        source.write_text("""OPENSEQ 'data' TO F ELSE ABORT
Alias = F
NOBUF Alias SETTING S ELSE ABORT
READSEQ Line FROM F ELSE ABORT
CRT Line:':':S
PROMPT ''
INPUT Answer
READSEQ Line FROM F ELSE ABORT
NOBUF F
WRITESEQ 'visible' TO F ELSE ABORT
CRT Line
INPUT Answer
CLOSESEQ F
""")
        binary = self.work / 'nobuf'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        with subprocess.Popen([binary], cwd=self.work, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), b'first:0\n')
                with data.open('r+b') as stream:
                    stream.seek(len(b'first\n'))
                    stream.write(b'new')
                proc.stdin.write(b'continue\n')
                proc.stdin.flush()
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), b'new\n')
                self.assertEqual(data.read_bytes(), b'first\nnew\nvisible\n')
                stdout, stderr = proc.communicate(b'done\n', timeout=5)
                self.assertEqual((proc.returncode, stdout, stderr), (0, b'', b''))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_nobuf_failure_status_and_diagnostic(self):
        data = self.work / 'data'
        data.write_bytes(b'line\n')
        source = self.work / 'nobuf.b'
        source.write_text("""OPENSEQ 'missing' TO Pending THEN ABORT
NOBUF Pending SETTING S THEN ABORT ELSE CRT S:':':STATUS()
OPENSEQ 'data' TO F ELSE ABORT
READSEQ Line FROM F ELSE ABORT
NOBUF F SETTING S
CRT S:':':STATUS()
NOBUF F
""")
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'128:128\n32768:32768\n')
        self.assertIn(f'{source}:7:1: NOBUF failed'.encode(), result.stderr)

    def test_timeout_on_regular_sequential_file(self):
        (self.work / 'data').write_bytes(b'line\nblock')
        source = self.work / 'timeout.b'
        source.write_text("""OPENSEQ 'data' TO F ELSE ABORT
Alias = F
TIMEOUT Alias, 60
READSEQ Line FROM F THEN CRT Line ELSE ABORT
TIMEOUT F, .5
READBLK Block FROM Alias, 5 THEN CRT Block ELSE ABORT
TIMEOUT F, 60
READSEQ Line FROM F SETTING S THEN ABORT ELSE CRT S:':':STATUS()
TIMEOUT Alias, 0
CRT STATUS()
READBLK Block FROM F, 1 SETTING S THEN ABORT ELSE CRT S:':':STATUS()
CLOSESEQ F
""")
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'line\nblock\n128:128\n128\n128:128\n')
        self.assertEqual(result.stderr, b'')

    def test_timeout_diagnostics(self):
        (self.work / 'data').write_bytes(b'line\n')
        source = self.work / 'timeout.b'
        for setup, operands, message in [
                ('', "'', 1", 'requires an open sequential handle'),
                ("OPENSEQ 'missing' TO F THEN ABORT\n", 'F, 1', 'requires an open sequential handle'),
                ("OPENSEQ 'data' TO F ELSE ABORT\nCLOSESEQ F\n", 'F, 1',
                 'requires an open sequential handle'),
                *[("OPENSEQ 'data' TO F ELSE ABORT\n", f'F, {seconds}',
                   'requires nonnegative decimal seconds') for seconds in ("''", "'text'", '-1')]]:
            with self.subTest(setup=setup, operands=operands):
                source.write_text(f'{setup}TIMEOUT {operands}\n')
                result = self.run_native(source, cwd=self.work)
                line = len(setup.splitlines()) + 1
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:{line}:1: TIMEOUT {message}'.encode(), result.stderr)

    def test_flush_null_handle(self):
        source = self.work / 'flush.b'
        source.write_text("F = ''\nFLUSH F ELSE CRT 'failed'\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:2:1: FLUSH requires an OPENSEQ handle'.encode(), result.stderr)

    def test_fileinfo_memory_handle(self):
        source = self.work / 'fileinfo.b'
        source.write_text("""CRT FILEINFO(F, 0)
OPEN 'missing' TO F THEN STOP
CRT FILEINFO(F, 0)
OPEN 'customers' TO F ELSE STOP
Path = FILEINFO(F, 2)
CRT FILEINFO(F, 0):':':Path:':':FILEINFO(Path, 0)
CLOSE F
CRT FILEINFO(F, 0):'[':FILEINFO(F, 2):']'
""")
        run = self.run_native(source, options=['--memory-file', 'customers'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\n0\n1:customers:0\n0[]\n')
        self.assertEqual(run.stderr, b'')

    def test_fileinfo_sequential_handle(self):
        source = self.work / 'fileinfo.b'
        source.write_text("""OPENSEQ 'report' TO F THEN STOP
CRT FILEINFO(F, 0)
WRITESEQ 'row' TO F ELSE STOP
CRT FILEINFO(F, 0)
CRT FILEINFO(F, 2)
Alias = F
CLOSESEQ F
CRT FILEINFO(Alias, 0):'[':FILEINFO(Alias, 2):']'
""")
        run = self.run_native(source, cwd=self.work)
        self.assertEqual(run.returncode, 0, run.stderr)
        path = os.fsencode(self.work.resolve() / 'report')
        self.assertEqual(run.stdout, b'0\n1\n' + path + b'\n0[]\n')
        self.assertEqual(run.stderr, b'')

    def test_fileinfo_unsupported_key(self):
        source = self.work / 'fileinfo.b'
        source.write_text("CRT FILEINFO(F, 1)\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: FILEINFO supports keys 0 and 2'.encode(), run.stderr)

    def test_data_queues_input_and_hands_it_to_commands(self):
        source = self.work / 'data.b'
        source.write_text("""PROMPT ''
FOR I = 1 TO 2
    DATA 'item-':I
NEXT I
DATA 'abc':@FM:'', 'next'
INPUT A
INPUT B
INPUT Prefix, 2
INPUT Suffix
INPUT EmptyLine
INPUT Last
CRT A:':':B:':':Prefix:':':Suffix:'[':EmptyLine:']:':Last
DATA 'child-1':@FM:'child-2', ''
EXECUTE 'cat' CAPTURING Captured RETURNING Result
CRT CONVERT(Captured, @FM, '|'):':':Result
DATA 'direct'
PERFORM 'cat'
DATA STR('x', 100000)
EXECUTE 'true'
INPUT FromStdin
CRT FromStdin
""")
        binary = self.work / 'data'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'fallback\n', capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'item-1:item-2:ab:c[]:next\nchild-1|child-2||:0\ndirect\nfallback\n')
        self.assertEqual(result.stderr, b'')
    def test_sequential_seek(self):
        path = self.work / 'data'
        path.write_bytes(b'abc\n12345\nlast\n')
        result = self.run_native(ROOT / 'tests/io/seek.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'345\n45\nlast\n0\nabc\n32768\n12345\n128\n')
        self.assertEqual(path.read_bytes(), b'aZ\n\n12345\nlast\nend\n\0\0gap\n')
        self.assertFalse((self.work / 'absent').exists())

    def test_seek_empty_operands(self):
        (self.work / 'data').touch()
        source = self.work / 'invalid.b'
        for args in ['F, 0, ""', 'F, ""', '""']:
            with self.subTest(args=args):
                source.write_text(f"OPENSEQ 'data' TO F ELSE STOP\nSEEK {args} ELSE STOP\n")
                result = self.run_native(source, cwd=self.work)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:2:1: SEEK requires nonempty'.encode(), result.stderr)

    def test_sequential_files(self):
        data = b'first\n\n' + b'x' * 1100 + b'\nlast'
        (self.work / 'input').write_bytes(data)
        result = self.run_native(ROOT / 'tests/io/sequential.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'0\nlocked -2\nbusy\n[first]\n[]\n1024\nlast\n'
                         b'eof 128\n24576\nclosed\nalready closed\nmissing\ndone\n')
        self.assertEqual((self.work / 'input').read_bytes(), data)
        self.assertEqual((self.work / 'new').read_bytes(), b'one\nTWO\nlast\nend\n')

    def test_sequential_external_lock_and_fifo(self):
        source = self.work / 'open.b'
        source.write_text("""OPENSEQ 'input' READONLY TO F LOCKED CRT 'locked' THEN STOP ELSE STOP
OPENSEQ 'pipe' TO F SETTING S ON ERROR CRT S THEN STOP ELSE STOP
""")
        os.mkfifo(self.work / 'pipe')
        with (self.work / 'input').open('wb') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'locked\n32768\n')

    def test_sequential_routine_lifetime(self):
        (self.work / 'input').write_bytes(b'hello\n')
        source = self.work / 'main.b'
        sub = self.work / 'sub.b'
        source.write_text("""CALL OPENER(0, ARG)
CALL OPENER(1, ARG)
READSEQ V FROM ARG ELSE STOP
CRT V
CLOSESEQ ARG
""")
        sub.write_text("""SUBROUTINE OPENER(KEEP, ARG)
OPENSEQ 'input' TO LOCAL ELSE STOP
IF KEEP THEN ARG = LOCAL
RETURN
""")
        result = self.run_native(source, sub, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'hello\n')

    def test_saved_lists_across_executables(self):
        directory = self.work / 'lists'
        directory.mkdir()
        env = dict(os.environ, JBCC_LIST_DIR=str(directory))
        written = self.run_native(ROOT / 'tests/io/write-lists.b', options=['--memory-file', 'F'], env=env)
        self.assertEqual((written.returncode, written.stdout, written.stderr), (0, b'0\nremaining 1,b\n', b''))
        self.assertFalse((self.work / 'order').exists())
        read = self.run_native(ROOT / 'tests/io/read-lists.b', env=env)
        self.assertEqual((read.returncode, read.stderr), (0, b''))
        self.assertEqual(read.stdout, b'4\n[first]\n[]\n[last]\n[]\nempty 0\nmissing 0\n7\nkeys 2\na\nb\n')

        deleted = self.run_native(ROOT / 'tests/io/delete-lists.b', env=env)
        self.assertEqual((deleted.returncode, deleted.stderr), (0, b''))
        self.assertEqual(deleted.stdout, b'4\nfirst\n3\n[]\n7\nmissing 0\ninactive\ncleared\n')
        check = self.work / 'check.b'
        check.write_text("GETLIST '../order' ELSE CRT 'gone'\nGETLIST 'empty' SETTING N THEN CRT N\n")
        after = self.run_native(check, env=env)
        self.assertEqual((after.returncode, after.stdout, after.stderr), (0, b'gone\n0\n', b''))

    def test_selected_tracks_default_external_list_across_calls(self):
        main = self.work / 'main.b'
        routine = self.work / 'replace.list.b'
        main.write_text("""WRITELIST 'one' ON ''
CALL REPLACE.LIST()
GETLIST 'named' TO L SETTING N THEN CRT N:':':@SELECTED ELSE STOP
""")
        routine.write_text("""SUBROUTINE REPLACE.LIST()
WRITELIST 'two':@FM:'three' ON ''
WRITELIST 'other' ON 'named'
""")
        env = dict(os.environ, JBCC_LIST_DIR=str(self.work))
        run = self.run_native(main, routine, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'1:2\n')
        self.assertEqual(run.stderr, b'')

    def test_cleardata_discards_the_queue_and_preserves_standard_input(self):
        source = self.work / 'cleardata.b'
        source.write_text("""PROMPT ''
CLEARDATA
DATA 'first':@FM:'discard this', 'discard this too'
INPUT First
IF First = 'first' THEN CLEARDATA
INPUT FromPipe
DATA 'fresh'
INPUT FromData
CLEARDATA = 'variable'
CRT First:':':FromPipe:':':FromData:':':CLEARDATA
""")
        binary = self.work / 'cleardata'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'pipe\n', capture_output=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, b'first:pipe:fresh:variable\n', b''))

    def test_record_id_survives_loop_collection_and_return(self):
        main = self.work / 'main.b'
        routine = self.work / 'select.id.b'
        main.write_text('CALL SELECT.ID()\nCRT @ID\n')
        routine.write_text("""SUBROUTINE SELECT.ID()
FOR I = 1 TO 4
    @ID = 'key-':I
NEXT I
""")
        run = self.run_native(main, routine)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'key-4\n')
        self.assertEqual(run.stderr, b'')

    def test_record_context_survives_collection_and_changes_only_on_explicit_writes(self):
        main = self.work / 'main.b'
        routine = self.work / 'seed.b'
        main.write_text("""CRT '[':@RECORD:']'
@ID = 'initial'
CALL SEED()
CRT @ID:':':@RECORD<2>
OPEN 'records' TO F ELSE ABORT
WRITE 'one':@FM:'two' TO F, 'key' ELSE ABORT
READ Other FROM F, 'key' ELSE ABORT
CRT @ID:':':@RECORD<2>
READ @RECORD FROM F, 'key' ELSE ABORT
CRT @ID:':':@RECORD<2>
SELECT 'next'
READNEXT @ID ELSE ABORT
CRT @ID:':':@RECORD<1>
READV @RECORD FROM F, 'key', 2 ELSE ABORT
CRT @ID:':':@RECORD
READU @RECORD FROM F, 'key' ELSE ABORT
CRT @ID:':':@RECORD<1>
READ @RECORD FROM F, 'missing' THEN ABORT ELSE CRT @ID:':[':@RECORD:']'
""")
        routine.write_text("""SUBROUTINE SEED()
FOR I = 1 TO 4
    @RECORD = 'seed':@FM:I
NEXT I
""")
        run = self.run_native(main, routine, options=['--memory-file', 'records'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'[]\ninitial:4\ninitial:4\ninitial:two\n'
                         b'next:one\nnext:two\nnext:one\nnext:[]\n')
        self.assertEqual(run.stderr, b'')

    def test_deletelist_requires_named_store(self):
        source = self.work / 'delete.b'
        source.write_text("DELETELIST 'batch'\n")
        result = self.run_native(source, env=dict(os.environ, JBCC_LIST_DIR=''))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:1: DELETELIST requires JBCC_LIST_DIR'.encode(), result.stderr)

    def test_saved_list_write_failure(self):
        source = self.work / 'failed.b'
        source.write_text("WRITELIST 'item' TO 'name' SETTING S ON ERROR CRT S\n")
        env = dict(os.environ, JBCC_LIST_DIR=str(self.work / 'missing'))
        result = self.run_native(source, env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'128\n', b''))

    def test_print_units(self):
        env = dict(os.environ, JBCC_PRINT_DIR=str(self.work))
        result = self.run_native(ROOT / 'tests/io/print-units.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'Screen 1\nscreen\nprogress\nback\nterminal\n\fScreen 2\nend\n')
        jobs = sorted((p.name.split('-')[1], p.read_bytes()) for p in self.work.glob('unit-*-*'))
        self.assertEqual(jobs, [
            ('0', b'Default 1\nfirst job\n\fDefault 2\n'),
            ('127', b'high\n'),
            ('2', b'Other 1\nA\tB\fOther 9\nseparate\nReset 1\n'),
            ('2', b'new job\n'),
        ])

    def test_report_diagnostics(self):
        source = self.work / 'report.b'
        for statement, message in [
                ('HEADING ON 1 "title"', 'printer output requires JBCC_PRINT_DIR'),
                ('PAGE ON 3', 'printer output requires JBCC_PRINT_DIR'),
                ('PRINT ON 128 "bad"', 'print unit must be an integer from 0 to 127'),
                ('PRINTER ON', 'printer output requires JBCC_PRINT_DIR'),
                ('PAGE 2.5', 'PAGE requires an integer page number'),
                ("HEADING \"'C'\"", 'unsupported HEADING option')]:
            with self.subTest(statement=statement):
                source.write_text(statement + '\n')
                result = self.run_native(source, env=dict(os.environ, JBCC_PRINT_DIR=''))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{source}:1:1: {message}".encode(), result.stderr)

    def test_diagnostics_preserve_existing_output(self):
        source = self.work / 'invalid.b'
        for program, location in [('N = 2\nIF N THEN\n', ':2:1:'),
                                  ('BEGIN CASE\nCRT 1\nEND CASE\n', ':1:1: expected CASE clause'),
                                  ('BEGIN CASE\nEND IF\n', ":2:5: expected 'CASE'"),
                                  ('BEGIN CASE END CASE\n', ':1:1: expected CASE clause'),
                                  ('CRT 1; EQU X TO 2,\n', ':1:18: unfinished EQUATE list'),
                                  ('CRT 1; EQU X TO; CRT 2\n', ':1:12: expected EQUATE name TO expression'),
                                  ('CALL F(1,\n', ':1:9: unfinished comma continuation'),
                                  ('CALL F(1,\n )\n', ':2:2: expected call argument'),
                                  ('CALL F(1\n, 2)\n', ":1:9: expected ')'"),
                                  ("OPEN '', 'F', 'X' ELSE STOP\n", ':1:13: expected THEN or ELSE'),
                                  ("OPEN '',, 'X' ELSE STOP\n", ':1:9: expected a variable'),
                                  ('REWIND ON 2\n', ':1:12: expected THEN or ELSE'),
                                  ('READT X\n', ':1:8: expected THEN or ELSE'),
                                  ("WRITET 'x'\n", ':1:11: expected THEN or ELSE'),
                                  ('WEOF\n', ':1:5: expected THEN or ELSE'),
                                  ('DEBUG 1\n', ":1:7: unexpected '1'"),
                                  ("IF 1 THEN CRT 1\n  ELSE CRT Missing\n", ":2:12: unknown variable"),
                                  ("CRT 'done'\nELSE CRT 1\n", ":2:1: unexpected 'ELSE'"),
                                  ("DIM A(2)\nMATREAD A FROM 'id'\n LOCKED STOP ELSE STOP\n",
                                   ":3:2: MATREAD LOCKED requires a locking file backend"),
                                  ('PROGRAM\n', ':1:8:'),
                                  ('FUNCTION F()\nF1: RETURN TO F1\n', ':2:5: RETURN TO is not allowed'),
                                  ('PROGRAM one two\n', ':1:13:'),
                                  ('N = 1\nN : = 2\n', ":2:1: unsupported statement 'N'"),
                                  ('N = 1\nN +\n= 2\n', ":2:1: unsupported statement 'N'"),
                                  ('GO = 1\nIF GO THEN CRT Missing\n', ':2:16: unknown variable'),
                                  ('PROGRAM GOTO\nCRT NeverAssigned\n', ':2:5:'),
                                  ('CRT 1 +\n', ':1:8:'),
                                  ('CRT UNKNOWN.FUNCTION(3)\n', ':1:5:'),
                                  ('INPUT X _\n', ':1:9: INPUT underscore requires a length'),
                                  ('@ID += 1\n', ":1:5: expected '='"),
                                  ('READNEXT @USERNO ELSE STOP\n', ":1:11: expected 'ID'"),
                                  ("READ @USERNO FROM 'key' ELSE ABORT\n",
                                   ':1:7: expected @ID or @RECORD as a record read destination'),
                                  ("CRT RND()\n", ":1:5: wrong argument count for 'RND'"),
                                  ("CRT DROUND(1, 2, 3)\n", ":1:5: wrong argument count for 'DROUND'"),
                                  ("CRT ADDS('x')\n", ":1:5: wrong argument count for 'ADDS'"),
                                  ("CRT SUBS(1)\n", ":1:5: wrong argument count for 'SUBS'"),
                                  ("CRT MULS(1, 2, 3)\n", ":1:5: wrong argument count for 'MULS'"),
                                  ("CRT REUSE(2) + 3\n", ':1:5: REUSE requires a direct multiplication operand'),
                                  ("CRT 2 * REUSE(3) ^ 4\n", ':1:9: REUSE requires a direct multiplication operand'),
                                  ("CRT SDIV(1)\n", ":1:5: wrong argument count for 'SDIV'"),
                                  ("CRT SDIV(1, 2, 3, 4)\n", ":1:5: wrong argument count for 'SDIV'"),
                                  ("CRT DIVS(1)\n", ":1:5: wrong argument count for 'DIVS'"),
                                  ("CRT CATS('x')\n", ":1:5: wrong argument count for 'CATS'"),
                                  ("CRT COMPARE('x')\n", ":1:5: wrong argument count for 'COMPARE'"),
                                  ("CRT NES(1, 2, 3)\n", ":1:5: wrong argument count for 'NES'"),
                                  ("CRT EQS('x')\n", ":1:5: wrong argument count for 'EQS'"),
                                  ('CRT NUM()\n', ":1:5: wrong argument count for 'NUM'"),
                                  ('CRT NUM(1, 2)\n', ":1:5: wrong argument count for 'NUM'"),
                                  ("CRT ICONV('20121231')\n", ":1:5: wrong argument count for 'ICONV'"),
                                  ("CRT FIELDS('x', ':')\n", ":1:5: wrong argument count for 'FIELDS'"),
                                  ("CRT STR('x')\n", ":1:5: wrong argument count for 'STR'"),
                                  ("CRT BYTELEN()\n", ":1:5: wrong argument count for 'BYTELEN'"),
                                  ("CRT REPLACE('a', 1, 'x')\n", ":1:24: expected ';'"),
                                  ("CRT DQUOTE()\n", ":1:5: wrong argument count for 'DQUOTE'"),
                                  ("CRT SQUOTE(1, 2)\n", ":1:5: wrong argument count for 'SQUOTE'"),
                                  ("CRT LN()\n", ":1:5: wrong argument count for 'LN'"),
                                  ("CRT EXP()\n", ":1:5: wrong argument count for 'EXP'"),
                                  ("CRT SQRT(1, 2)\n", ":1:5: wrong argument count for 'SQRT'"),
                                  ("CRT PWR(2)\n", ":1:5: wrong argument count for 'PWR'"),
                                  ("CRT SUMMATION(1, 2)\n", ":1:5: wrong argument count for 'SUMMATION'"),
                                  ("CRT TRIMS('a', 'b')\n", ":1:5: wrong argument count for 'TRIMS'"),
                                  ("CRT REM(1)\n", ":1:5: wrong argument count for 'REM'"),
                                  ("CRT MOD(1)\n", ":1:5: wrong argument count for 'MOD'"),
                                  ("CRT LEFT('x')\n", ":1:5: wrong argument count for 'LEFT'"),
                                  ("CRT RIGHT('x',1,2)\n", ":1:5: wrong argument count for 'RIGHT'"),
                                  ("CRT DELETE('a')\n", ":1:5: wrong argument count for 'DELETE'"),
                                  ("CRT DELETE('a',1,2,3,4)\n", ":1:5: wrong argument count for 'DELETE'"),
                                  ("CRT EXTRACT('a')\n", ":1:5: wrong argument count for 'EXTRACT'"),
                                  ("CRT EXTRACT('a',1,2,3,4)\n", ":1:5: wrong argument count for 'EXTRACT'"),
                                  ("CRT MINIMUM()\n", ":1:5: wrong argument count for 'MINIMUM'"),
                                  ("CRT MAXIMUM(1, 2)\n", ":1:5: wrong argument count for 'MAXIMUM'"),
                                  ("CRT SUBSTRINGS('x', 1)\n", ":1:5: wrong argument count for 'SUBSTRINGS'"),
                                  ("CRT SPLICE('a', 'b')\n", ":1:5: wrong argument count for 'SPLICE'"),
                                  ("CRT TRIMF()\n", ":1:5: wrong argument count for 'TRIMF'"),
                                  ("CRT TRIMB('a', 'b')\n", ":1:5: wrong argument count for 'TRIMB'"),
                                  ("CRT ALPHA()\n", ":1:5: wrong argument count for 'ALPHA'"),
                                  ("CRT ALPHA('a', 'b')\n", ":1:5: wrong argument count for 'ALPHA'"),
                                  ("CRT NEG()\n", ":1:5: wrong argument count for 'NEG'"),
                                  ("CRT NEG(1, 2)\n", ":1:5: wrong argument count for 'NEG'"),
                                  ("CRT UPCASE()\n", ":1:5: wrong argument count for 'UPCASE'"),
                                  ("CRT LOWCASE(1, 2)\n", ":1:5: wrong argument count for 'LOWCASE'"),
                                  ('CRT GETENV("x", 1)\n', ':1:17: expected a name'),
                                  ('CRT PUTENV("A", "B")\n', ":1:5: wrong argument count for 'PUTENV'"),
                                  ('R <1 = 2\n', ":1:3: expected closing '>' for dynamic-array assignment"),
                                  ('R <1,2,3,4> = 0\n', ':1:3: expected one to three dynamic-array indices'),
                                  ('CLOSE\n', ':1:6: expected a name'),
                                  ('CLOSE F,G ON ERROR NULL\n', ":1:11: unexpected 'ON'"),
                                  ('CRT DATE(1)\n', ':1:5:'),
                                  ('CRT TIME(1)\n', ':1:5:'),
                                  ('CRT TIMEDATE(1)\n', ':1:5:'),
                                  ('FOR I = 1 TO 2\nNEXT J = 7\n', ":2:8: unexpected '='"),
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

    def test_insert_diagnostics(self):
        source = self.work / 'insert.b'
        for program, message in [
                ("CRT INSERT('a', 1, 'x')", ":1:23: expected ';'"),
                ("CRT INSERT('a', 1; 'x', 2)", ":1:23: expected ')'")]:
            with self.subTest(program=program):
                source.write_text(program + '\n')
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + message, run.stderr)
        source.write_text("CRT INSERT('a', 'bad'; 'x')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: expected a numeric value'.encode(), run.stderr)

    def test_delete_function_rejects_nonnumeric_index(self):
        source = self.work / 'delete.b'
        source.write_text("CRT DELETE('a', 99, 'bad', 0)\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: DELETE requires numeric indices'.encode(), run.stderr)

    def test_extract_rejects_nonnumeric_index(self):
        source = self.work / 'extract.b'
        source.write_text("CRT EXTRACT('a', 99, 'bad', 0)\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: EXTRACT requires numeric indices'.encode(), run.stderr)

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

    def test_stop_and_abort_from_main(self):
        source = self.work / 'main.b'
        for statement, status, message in [
            ("STOP", 0, b""),
            ("STOP 'cannot read ' : 'file'", 0, b"cannot read file\n"),
            ("ABORT", 1, b""),
            ("ABORT 201, 'file', 1 + 2", 1, b"ABORT [201] file 3\n"),
        ]:
            with self.subTest(statement=statement):
                source.write_text("CRT 'before'\n" + statement + "\nCRT 'unreachable'\n")
                run = self.run_native(source)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (status, b'before\n', message))

    def test_stop_and_abort_from_routine(self):
        main = self.work / 'main.b'
        sub = self.work / 'finish.b'
        main.write_text("CALL FINISH('data')\nPRINT 'unreachable caller'\n")
        for statement, status, message in [
            ("IF 1 THEN STOP 201, Name ELSE STOP", 0, b"STOP [201] data\n"),
            ("IF 0 THEN STOP ELSE ABORT 'missing', Name", 1, b"missing data\n"),
        ]:
            with self.subTest(statement=statement):
                sub.write_text("SUBROUTINE FINISH(Name)\n" + statement + "\nCRT 'unreachable'\n")
                run = self.run_native(main, sub)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (status, b'', message))

    def test_stop_missing_message_argument(self):
        source = self.work / 'main.b'
        source.write_text("STOP 201,, 'file'\n")
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:10: expected a variable", result.stderr)

    def test_mismatched_next_counter(self):
        source = ROOT / 'tests/programs/mismatched-next.b'
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(build.stderr.splitlines(), [
            f'{source}:4:10: warning: NEXT Outer closes FOR Inner',
            f'{source}:6:6: warning: NEXT Unused closes FOR Outer',
        ])
        run = subprocess.run([binary], capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'1.1\n1.3\ninner 5\n2.1\n2.3\ninner 5\nouter 3\n')

    def test_loop_exit_control_flow_diagnostics(self):
        source = self.work / 'exit.b'
        binary = self.work / 'program'
        for keyword in ('EXIT', 'BREAK'):
            with self.subTest(keyword=keyword):
                source.write_text(f"LOOP\nIF 1 THEN {keyword}\nX = 2\nUNTIL 1 REPEAT\nPRINT X\n")
                build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(build.returncode, 0)
                self.assertIn(f"{source}:5:7: unknown variable", build.stderr)
                source.write_text(f"  {keyword}\nPRINT 'after'\n")
                build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                self.assertIn(f'{source}:1:3: warning: {keyword} outside a loop ignored', build.stderr)
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

    def test_conditional_expression_calls(self):
        main = self.work / 'main.b'
        function = self.work / 'BUMP'
        function.write_text('FUNCTION BUMP(N)\nN += 1\nRETURN(N)\n')
        main.write_text("DEFFUN BUMP()\nN = 0\n"
                        "CRT IF 0 THEN BUMP(N) ELSE 7, N\n"
                        "CRT IF 1 THEN BUMP(N) ELSE BUMP(N), N\n"
                        "CRT N + (IF N THEN BUMP(N) ELSE 0), N\n")
        run = self.run_native(main, function)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, b'7\t0\n1\t1\n3\t2\n', b''))

        main.write_text("DEFFUN BUMP()\nValue = IF 0 THEN BUMP(X) ELSE 7\nCRT X\n")
        run = subprocess.run([CLI, main, function, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{main}:3:5: unknown variable', run.stderr)

    def test_conditional_expression_requires_else(self):
        source = self.work / 'bad.b'
        source.write_text("Value = IF 1 THEN 2\n")
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:20: expected 'ELSE'", result.stderr)

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

    def test_startup_clock_is_shared_across_midnight(self):
        main = self.work / 'main.b'
        routine = self.work / 'show.start.b'
        main.write_text("CRT OCONV(DATE(),'D-'):':':TIME()\nCALL SHOW.START()\n")
        # Start one second before midnight in UTC+1.
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
        binary = self.work / 'startup-clock'
        for statements, expected in [
                ("CRT OCONV(@DATE,'D-'):':':@TIME\nCRT @TIME", '12-31-2023:86399\n86399\n'),
                ('CRT @TIME', '86399\n'),
                ("CRT OCONV(@DATE,'D-')", '12-31-2023\n')]:
            with self.subTest(statements=statements):
                routine.write_text('SUBROUTINE SHOW.START()\n' + statements + '\n')
                subprocess.run([CLI, main, routine, '-o', self.c], check=True)
                subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                                '-Dtime=test_clock', self.c, clock, '-o', binary], check=True)
                run = subprocess.run([binary], env=dict(os.environ, TZ='UTC+1'), capture_output=True,
                                     text=True, check=True)
                self.assertEqual(run.stdout, '01-01-2024:1\n' + expected)
                self.assertEqual(run.stderr, '')

    def test_iconv_diagnostics(self):
        source = self.work / 'date.b'
        cases = [
            ("'20121231', 'MD2'", "unsupported ICONV mask 'MD2'"),
            ("'24:00', 'MT'", "ICONV time requires a valid H:MM or H:MM:SS"),
            ("'0:00 AM', 'MTS'", "ICONV time requires a valid H:MM or H:MM:SS"),
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

    def test_iconvs_empty_mask_diagnostic(self):
        source = self.work / 'iconvs.b'
        source.write_text("CRT ICONVS('', '')\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:5: ICONVS requires a conversion mask'.encode(), result.stderr)

    def test_oconvs_empty_mask_diagnostic(self):
        source = self.work / 'oconvs.b'
        source.write_text("CRT OCONVS('', '')\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:5: OCONVS requires a conversion mask'.encode(), result.stderr)

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

    def test_str_repetition(self):
        source = self.work / 'repeat.b'
        source.write_text("LongString = STR('long string ', 999)\nCRT LongString\n")
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'long string ' * 999 + b'\n')
        self.assertEqual(run.stderr, b'')

        for count, message in [("'two'", 'expected a numeric value'),
                               ("'9223372036854775807'", 'STR result too large')]:
            with self.subTest(count=count):
                source.write_text(f"CRT STR('abc', {count})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {message}'.encode(), run.stderr)

    def test_spaces_diagnostics(self):
        source = self.work / 'spaces.b'
        for argument, message in [
            ("''", 'SPACES requires nonempty elements'),
            ('@FM:2', 'SPACES requires nonempty elements'),
            ('2:@VM:@SM:3', 'SPACES requires nonempty elements'),
            ('2:@SM', 'SPACES requires nonempty elements'),
            ("2:@FM:'bad'", 'expected a numeric value'),
            ('9223372036854775807:@FM:9223372036854775807', 'SPACES result too large'),
        ]:
            with self.subTest(argument=argument):
                source.write_text(f'CRT SPACES({argument})\n')
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:1:5: {message}'.encode(), result.stderr)

    def test_left_right_require_numeric_length(self):
        source = self.work / 'length.b'
        for name in ('LEFT', 'RIGHT'):
            with self.subTest(name=name):
                source.write_text(f"CRT {name}('', 'bad')\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: expected a numeric value'.encode(), run.stderr)

    def test_suffix_requires_numeric_length(self):
        source = self.work / 'suffix.b'
        source.write_text("CRT 'abc'['bad']\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:10: expected a numeric value'.encode(), run.stderr)

    def test_substrings_requires_numeric_bounds(self):
        source = self.work / 'substrings.b'
        for args in ("'x', 1", "1, 'x'"):
            with self.subTest(args=args):
                source.write_text(f"CRT SUBSTRINGS('', {args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: expected a numeric value'.encode(), run.stderr)

    def test_splice_reuse_scalar(self):
        source = self.work / 'main.b'
        bump = self.work / 'bump.b'
        source.write_text("DEFFUN BUMP(N)\nN = 0\n"
                          "CRT SPLICE(REUSE(BUMP(N)), ':', 'a':@FM:'b')\nCRT N\n")
        bump.write_text('FUNCTION BUMP(N)\nN += 1\nRETURN N\n')
        run = self.run_native(source, bump)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'1:a\xfe1:b\n1\n')

        source.write_text("CRT SPLICE('x', ':', REUSE('a':@VM:'b'))\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:22: REUSE in SPLICE requires a scalar'.encode(), run.stderr)

    def test_eqs_reuse_requires_scalar(self):
        source = self.work / 'eqs.b'
        source.write_text("CRT EQS(REUSE('a':@VM:'b'), 'a')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:9: REUSE in EQS requires a scalar'.encode(), run.stderr)

    def test_compare_invalid_justification(self):
        source = self.work / 'compare.b'
        source.write_text("CRT COMPARE('left', 'right', 'X')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: COMPARE justification must be L or R'.encode(), run.stderr)

    def test_fold_invalid_width(self):
        source = self.work / 'fold.b'
        for width in ("-1", "1.5", "'bad'"):
            with self.subTest(width=width):
                source.write_text(f"CRT FOLD('text', {width})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: FOLD width must be a nonnegative integer'.encode(), run.stderr)

    def test_fmts_invalid_mask(self):
        source = self.work / 'fmts.b'
        for args, mask in [("1:@FM:2, ''", ''), ("'', 'R?'", 'R?')]:
            with self.subTest(mask=mask):
                source.write_text(f"CRT FMTS({args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f"{source}:1:5: unsupported FMT mask '{mask}'".encode(), run.stderr)

    def test_dround_diagnostics(self):
        source = self.work / 'dround.b'
        for args, diagnostic in [
                ("'text'", "DROUND requires a numeric value"),
                ("1, -1", "DROUND precision requires a nonnegative integer"),
                ("1, 1.5", "DROUND precision requires a nonnegative integer"),
                ("1, ''", "DROUND precision requires a nonnegative integer")]:
            with self.subTest(args=args):
                source.write_text(f'CRT DROUND({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {diagnostic}'.encode(), run.stderr)

    def test_rewind_invalid_channel(self):
        source = self.work / 'rewind.b'
        for operand in ("ON -1", "FROM 10", "UNIT(2.5)", "ON 'text'"):
            with self.subTest(operand=operand):
                source.write_text(f"REWIND {operand} ELSE CRT 'unexpected branch'\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(f'{source}:1:1: REWIND channel must be an integer from 0 to 9'.encode(),
                              result.stderr)

    def test_readt_invalid_channel(self):
        source = self.work / 'readt.b'
        for statement in ("READT X FROM 10", "READT UNIT(2.5) X"):
            with self.subTest(statement=statement):
                source.write_text(f"{statement} ELSE CRT 'unexpected branch'\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(f'{source}:1:1: READT channel must be an integer from 0 to 9'.encode(),
                              result.stderr)

    def test_writet_diagnostics(self):
        source = self.work / 'writet.b'
        for statement, diagnostic in [
                ("WRITET 'data' TO 10", ":1:1: WRITET channel must be an integer from 0 to 9"),
                ("WRITET UNIT(-1) 'data'", ":1:1: WRITET channel must be an integer from 0 to 9"),
                ("WRITET 1 / 0", ":1:10: division by zero")]:
            with self.subTest(statement=statement):
                source.write_text(f"{statement} ELSE CRT 'unexpected branch'\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn((str(source) + diagnostic).encode(), result.stderr)

    def test_callonexit_dispatches_linked_callbacks(self):
        source = self.work / 'exit.b'
        save = self.work / 'save.b'
        show = self.work / 'show.b'
        wrong = self.work / 'wrong.b'
        save.write_text("""SUBROUTINE SAVE.ARG(Arg)
COMMON /EXIT.DATA/ Saved
Saved = Arg
CRT 'save'
""")
        show.write_text("""SUBROUTINE SHOW.ARG(Arg)
COMMON /EXIT.DATA/ Saved
CRT '[':Arg:'] ':Saved
""")
        wrong.write_text("SUBROUTINE WRONG()\nCRT 'unexpected callback'\n")
        program = """Name = 'SAVE.ARG'
FOR I = 1 TO 2
    CRT CALLONEXIT(Name:@VM:'payload':@VM:I)
NEXT I
CRT CALLONEXIT('SHOW.ARG')
CRT CALLONEXIT('MISSING') > 0
CRT CALLONEXIT('WRONG') > 0
CRT CALLONEXIT('') > 0
CRT 'main'
"""
        for ending, status in (('', 0), ('STOP', 0), ('EXIT(7)', 7), ('ABORT', 1), ('DEBUG', 1)):
            with self.subTest(ending=ending):
                source.write_text(program + ending + '\n')
                result = self.run_native(source, save, show, wrong)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, b'0\n0\n0\n1\n1\n1\nmain\nsave\n[] payload\xfd1\n')
                if ending == 'DEBUG':
                    self.assertIn(b'DEBUG requires a jBC debugger', result.stderr)
                else:
                    self.assertEqual(result.stderr, b'')

    def test_debug_reports_location_only_when_reached(self):
        source = self.work / 'debug.b'
        source.write_text("""DEBUG = 'before'
IF 0 THEN DEBUG
CRT DEBUG
IF 1 THEN DEBUG
CRT 'after'
""")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'before\n')
        self.assertEqual(result.stderr, f'{source}:4:11: DEBUG requires a jBC debugger\n'.encode())

    def test_weof_invalid_channel(self):
        source = self.work / 'weof.b'
        for operand in ('ON 10', 'UNIT(-1)', "FROM 'text'"):
            with self.subTest(operand=operand):
                source.write_text(f"WEOF {operand} ELSE CRT 'unexpected branch'\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(f'{source}:1:1: WEOF channel must be an integer from 0 to 9'.encode(),
                              result.stderr)

    def test_smul_diagnostics(self):
        source = self.work / 'smul.b'
        for args, diagnostic in [
                ("'text', 2", "SMUL requires numeric operands"),
                ("1, '', 2", "SMUL requires numeric operands"),
                ("0, 2, -2", "SMUL precision requires -1 or a nonnegative integer"),
                ("1, 2, 1.5", "SMUL precision requires -1 or a nonnegative integer")]:
            with self.subTest(args=args):
                source.write_text(f'CRT SMUL({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {diagnostic}'.encode(), run.stderr)

    def test_sdiv_diagnostics(self):
        source = self.work / 'sdiv.b'
        for args, diagnostic in [
                ("'', 2", "SDIV requires numeric operands"),
                ("1, 'text'", "SDIV requires numeric operands"),
                ("0, '-0.00'", "SDIV division by zero"),
                ("1, 2, -2", "SDIV precision requires -1 or a nonnegative integer"),
                ("1, 2, 1.5", "SDIV precision requires -1 or a nonnegative integer")]:
            with self.subTest(args=args):
                source.write_text(f'CRT SDIV({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {diagnostic}'.encode(), run.stderr)

    def test_adds_diagnostics(self):
        source = self.work / 'adds.b'
        for args, diagnostic in [
                ("1:@VM:'bad', REUSE(2)", ':1:5: arithmetic requires numeric operands'),
                ("9223372036854775807, 1", ':1:5: integer addition overflow'),
                ("REUSE(1:@VM:2), 3", ':1:10: REUSE in ADDS requires a scalar')]:
            with self.subTest(args=args):
                source.write_text(f'CRT ADDS({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_infix_reuse_requires_scalar(self):
        source = self.work / 'reuse.b'
        source.write_text("CRT 2 * REUSE(3:@VM:4)\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:9: REUSE in multiplication requires a scalar'.encode(),
                      result.stderr)

    def test_muls_diagnostics(self):
        source = self.work / 'muls.b'
        for args, diagnostic in [
                ("3, 'bad'", ':1:5: arithmetic requires numeric operands'),
                ("1:@VM:4611686018427387904, REUSE(2)", ':1:5: integer multiplication overflow'),
                ("2, REUSE(3:@FM:4)", ':1:13: REUSE in MULS requires a scalar')]:
            with self.subTest(args=args):
                source.write_text(f'CRT MULS({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_divs_substitutes_zero_for_zero_divisors(self):
        source = self.work / 'divs.b'
        source.write_text("CRT DIVS(4:@VM:12:@VM:9:@VM:'', '-0.00':@VM:3:@VM:'00':@VM:0:@VM:0)\n"
                          "CRT 'continued'\n")
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\xfd4\xfd0\xfd\xfd0\ncontinued\n')
        warning = f'{source}:1:5: warning: DIVS: division by zero\n'
        self.assertEqual(run.stderr, warning.encode() * 2)

    def test_divs_diagnostics(self):
        source = self.work / 'divs.b'
        for args, diagnostic in [
                ("4:@VM:6, 2:@VM:'bad'", ':1:5: arithmetic requires numeric operands'),
                ("REUSE(3:@FM:4), 2", ':1:10: REUSE in DIVS requires a scalar')]:
            with self.subTest(args=args):
                source.write_text(f'CRT DIVS({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_subs_diagnostics(self):
        source = self.work / 'subs.b'
        for args, diagnostic in [
                ("1:@VM:'bad', 2", ':1:5: arithmetic requires numeric operands'),
                ("'', 'bad'", ':1:5: arithmetic requires numeric operands'),
                ("'-9223372036854775808', 1", ':1:5: integer subtraction overflow'),
                ("2, REUSE(3:@FM:4)", ':1:13: REUSE in SUBS requires a scalar')]:
            with self.subTest(args=args):
                source.write_text(f'CRT SUBS({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_ln_diagnostics(self):
        source = self.work / 'ln.b'
        for value, message in [("'abc'", 'requires a numeric operand'),
                               ('0', 'requires a positive operand'),
                               ('-1', 'requires a positive operand'),
                               ("STR('9', 5000)", 'operand out of range'),
                               ("'0.' : STR('0', 5000) : '1'", 'operand out of range')]:
            with self.subTest(value=value):
                source.write_text(f"CRT LN({value})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: LN {message}'.encode(), run.stderr)

    def test_exp_diagnostics(self):
        source = self.work / 'exp.b'
        for value, message in [("'x'", 'requires a numeric operand'),
                               ("STR('9', 5000)", 'operand out of range'),
                               ('20000', 'result out of range')]:
            with self.subTest(value=value):
                source.write_text(f"CRT EXP({value})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: EXP {message}'.encode(), run.stderr)

    def test_sqrt_diagnostics(self):
        source = self.work / 'sqrt.b'
        for value, message in [('-1', 'requires a nonnegative operand'),
                               ("'text'", 'requires a numeric operand'),
                               ("STR('9', 5000)", 'operand out of range'),
                               ("'0.' : STR('0', 5000) : '1'", 'operand out of range')]:
            with self.subTest(message=message):
                source.write_text(f"CRT SQRT({value})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: SQRT {message}'.encode(), run.stderr)

    def test_power_domain_and_diagnostics(self):
        source = self.work / 'power.b'
        for expr, column, message, continues in [
                ("PWR(-2, 0.5)", 5, "negative base with fractional exponent", True),
                ("0 ^ -2", 7, "zero raised to a negative power", False),
                ("2 ** 'x'", 7, "PWR requires numeric operands", False),
                ("PWR(10, 10000)", 5, "PWR result out of range", False)]:
            with self.subTest(expr=expr):
                source.write_text(f"CRT {expr}\nCRT 'done'\n")
                run = self.run_native(source)
                self.assertEqual(run.returncode == 0, continues)
                self.assertEqual(run.stdout, b'0\ndone\n' if continues else b'')
                self.assertIn(f'{source}:1:{column}: {message}'.encode(), run.stderr)

    def test_rnd_invalid_bound(self):
        source = self.work / 'rnd.b'
        for bound, diagnostic in [('1.5', 'requires an integer bound'),
                                  ("'x'", 'requires an integer bound'),
                                  ('0', 'requires a nonzero bound'),
                                  ('-2147483648', 'bound exceeds 2147483647'),
                                  ("'100000000000000000000'", 'bound exceeds 2147483647')]:
            with self.subTest(bound=bound):
                source.write_text(f"CRT RND({bound})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: RND {diagnostic}'.encode(), run.stderr)

    def test_mod_requires_numeric_operands(self):
        source = self.work / 'mod.b'
        for name, args in [('MOD', "'x', 0"), ('MOD', "1, 'x'"), ('REM', "1, 'x'")]:
            with self.subTest(name=name, args=args):
                source.write_text(f"CRT {name}({args})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {name} requires numeric operands'.encode(), run.stderr)

    def test_case_conversion_bytes(self):
        source = self.work / 'case.b'
        source.write_text("""Text = ''
FOR I = 1 TO 255
    Text := CHAR(I)
NEXT I
CRT UPCASE(Text)
CRT DOWNCASE(Text)
CRT LOWCASE(Text)
CRT Text
CRT UPCASE(''):LOWCASE('')
""")
        run = self.run_native(source)
        data = bytes(range(1, 256))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'\n'.join([data.upper(), data.lower(), data.lower(), data, b'', b'']))
        self.assertEqual(run.stderr, b'')

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

    def test_neg_substitutes_zero(self):
        source = self.work / 'neg.b'
        source.write_text("CRT NEG('qwert') + 2\nCRT 'continued'\n")
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'2\ncontinued\n')
        self.assertEqual(run.stderr, f'{source}:1:5: warning: NEG: Non-numeric value -- ZERO USED\n'.encode())

    def test_negs_warns_for_nonnumeric_elements(self):
        source = self.work / 'negs.b'
        source.write_text("CRT CONVERT(NEGS('bad':@FM:1:@VM:'' :@SM:'text'),@FM:@VM:@SM,'|^~')\n")
        result = self.run_native(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'0|-1^~0\n')
        warning = f'{source}:1:13: warning: NEGS: Non-numeric value -- ZERO USED\n'
        self.assertEqual(result.stderr, warning.encode() * 2)

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

    def test_abss_diagnostics(self):
        source = self.work / 'abss.b'
        source.write_text("CRT ABSS('-2':@VM:'not numeric')\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:5: ABSS requires numeric elements'.encode(), run.stderr)

    def test_fmt_diagnostics(self):
        source = self.work / 'fmt.b'
        for mask in ['D4/', 'R20', 'R%', "3'xx'R", 'R2,', '0T']:
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

    def test_div_requires_nonzero_numeric_operands(self):
        source = self.work / 'div.b'
        for args, diagnostic in [('7, 0.0', 'division by zero'),
                                 ("'x', 2", 'arithmetic requires numeric operands'),
                                 ("7, 'x'", 'arithmetic requires numeric operands')]:
            with self.subTest(args=args):
                source.write_text(f'CRT DIV({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {diagnostic}'.encode(), run.stderr)

    def test_compound_division_by_zero(self):
        source = self.work / 'division.b'
        source.write_text('N = 7\nN /   = 0\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:2:3: division by zero'.encode(), run.stderr)

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

    def test_bang_subroutine_names(self):
        main = self.work / 'main.b'
        plain = self.work / 'plain.b'
        bang = self.work / 'bang.b'
        main.write_text('X = 0\nCALL ADD.IT$(X)\nCALL !ADD.IT$(X); ! trailing comment\n'
                        'IF 0!X THEN CALL !ADD.IT$(X)\n!ADD.IT$(X) is a comment here\nCRT X\n')
        plain.write_text('SUB ADD.IT$(N)\nN += 1\nRETURN\n')
        bang.write_text('SUBROUTINE !ADD.IT$(N)\nN += 10\nRETURN\n')
        run = self.run_native(main, plain, bang)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'21\n')
        self.assertEqual(run.stderr, b'')

    def test_call_aliases_and_expression_arguments(self):
        caller = self.work / 'caller.b'
        callee = self.work / 'callee.b'
        caller.write_text('X = 1\nCALL TWICE(X, X)\nCALL TWICE(X + 1, X)\nPRINT X\n')
        callee.write_text('SUBROUTINE TWICE(A, B)\nA += 1\nB += A\nRETURN\n')
        run = self.run_native(callee, caller)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'10\n')

    def test_indirect_call(self):
        main = self.work / 'main.b'
        work = self.work / 'work.b'
        done = self.work / 'done.b'
        switch = self.work / 'switch.b'
        main.write_text("EQU Which TO Name\nDEFFUN SWITCH(N)\nDIM M(2)\nM(1) = 4\nX = 1\nName = '!WORK'\n"
                        "CALL @Which(MAT M, X, X, SWITCH(Name))\nCRT M(1), X\nCALL @ Name\n")
        work.write_text("SUBROUTINE !WORK(MAT A, B, C, D)\nA(1) += D\nB += A(1)\nC += 1\n")
        switch.write_text("FUNCTION SWITCH(N)\nN = 'DONE'\nRETURN 2\n")
        done.write_text("SUBROUTINE DONE()\nCRT 'done'\n")
        run = self.run_native(main, work, switch, done)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'6\t8\ndone\n')
        self.assertEqual(run.stderr, b'')

    def test_indirect_call_diagnostics(self):
        main = self.work / 'main.b'
        sub = self.work / 'update.b'
        sub.write_text("SUBROUTINE UPDATE(MAT M)\nCRT 'unexpected'\n")
        for name, args, units, message in [
                ('MISSING', '', [], 'unknown subroutine'),
                ('update', '(MAT M)', [sub], 'unknown subroutine'),
                ('UPDATE', '()', [sub], 'incompatible arguments for subroutine'),
                ('UPDATE', '(M(1))', [sub], 'incompatible arguments for subroutine')]:
            with self.subTest(name=name, args=args):
                main.write_text(f"DIM M(2)\nName = '{name}'\nCALL @Name{args}\n")
                run = self.run_native(main, *units)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, b'')
                self.assertIn(f"{main}:3:6: {message} '{name}'".encode(), run.stderr)

    def test_multiline_call(self):
        caller = self.work / 'caller.b'
        callee = self.work / 'callee.b'
        caller.write_text("""X = 4
R<1,2> = 3
CALL MIX(X + 1, ;* capture the first argument

    * pass X twice by reference
    X,
    ! extract from a dynamic array
    R<1,
      2>,
    X)
CRT X
""")
        callee.write_text('SUBROUTINE MIX(A, B,\nC, D)\nB = A * 10 + C\nD += B\nRETURN\n')
        run = self.run_native(caller, callee)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'106\n')

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

    def test_indexed_jump_selector(self):
        source = self.work / 'dispatch.b'
        function = self.work / 'pick.b'
        function.write_text('FUNCTION PICK(N)\nN += 1\nRETURN N\n')
        source.write_text('DEFFUN PICK(N)\nN = 1\nON PICK(N) GOSUB first, second\nCRT N\nSTOP\n'
                          "first: CRT 'first'; RETURN\nsecond: CRT 'second'; RETURN\n")
        run = self.run_native(source, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'second\n2\n')
        for value in ["'word'", '1.5']:
            source.write_text(f'ON {value} GOTO target\ntarget: STOP\n')
            run = self.run_native(source)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f'{source}:1:1: ON requires an integer selector'.encode(), run.stderr)

    def test_indexed_jump_range(self):
        source = self.work / 'range.b'
        source.write_text("ON 0 GOSUB low, high\nON '999999999999999999999' GOTO low, high\n"
                          "CRT 'fell through'\nSTOP\nlow: CRT 'low'; RETURN\nhigh: CRT 'high'; STOP\n")
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'low\nhigh\n')
        expected = [f'{source}:{line}:1: warning: ON selector out of range, using label {line}'
                    for line in (1, 2)]
        self.assertEqual(run.stderr.decode().splitlines(), expected)
        binary = self.work / 'pick'
        env = dict(os.environ, CC_FLAGS='-DJBCC_ON_FALLTHROUGH')
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True, env=env)
        run = subprocess.run([binary], capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, b'fell through\n')
        self.assertEqual(run.stderr, b'')

    def test_jump_cannot_bypass_for_header(self):
        source = self.work / 'jump.b'
        for jump, target in [('GOTO', 'middle'), ('GOTO', 'middle:'), ('GO', 'middle'), ('GO TO', 'middle:'),
                             ('GOSUB', 'middle'), ('GOSUB', 'middle:'),
                             ('ON 2 GO TO safe,', 'middle'), ('ON 2 GOTO safe,', 'middle'), ('ON 2 GOSUB safe,', 'middle')]:
            with self.subTest(jump=jump, target=target):
                source.write_text(f'{jump} {target}\nFOR I = 1 TO 2 STEP 1 + 1\nmiddle: PRINT I\nNEXT I\nsafe: STOP\n')
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{source}:1:{len(jump) + 2}: jump to 'middle' would bypass a FOR header",
                              result.stderr)

    def test_return_to_unwinds_subroutine(self):
        main = self.work / 'main.b'
        sub = self.work / 'sub.b'
        main.write_text('CALL CHECK()\nCRT "back in main"\n')
        sub.write_text('SUBROUTINE CHECK()\nGOSUB outer\nCRT "unexpected"\nRETURN\n'
                       'outer: GOSUB aborting\nCRT "unexpected"\nRETURN\n'
                       'aborting: CRT "unwind"\nRETURN TO aborting\n')
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'unwind\nunwind\nunwind\nback in main\n')

    def test_return_to_without_caller(self):
        main = self.work / 'main.b'
        main.write_text('GOSUB noop\nendhere: RETURN TO endhere\nnoop: RETURN\n')
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{main}:2:10: RETURN TO without an outstanding GOSUB".encode(), run.stderr)

    def test_return_to_bypasses_for_header(self):
        main = self.work / 'main.b'
        main.write_text('GOSUB redirect\nFOR I = 1 TO 2\nmiddle: CRT I\nNEXT I\n'
                        'redirect: RETURN TO middle\n')
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{main}:1:7: RETURN TO would bypass a FOR header".encode(), run.stderr)

    def test_bad_routine_references(self):
        main = self.work / 'main.b'
        sub = self.work / 'sub.b'
        sub.write_text('SUBROUTINE CHECK(X)\nRETURN\n')
        for program, message in [('CALL CHECK()', 'wrong argument count'),
                                 ('CALL MISSING()', 'unknown subroutine'),
                                 ('CALL !CHECK(X)', ":1:6: unknown subroutine '!CHECK'"),
                                 ('CALL ! CHECK(X)', ":1:6: expected a routine name immediately after '!'"),
                                 ('GOSUB missing', 'unknown label'),
                                 ('GOSUB missing:', ":1:7: unknown label 'missing'"),
                                 ('GO missing', ":1:4: unknown label 'missing'"),
                                 ('GO   TO missing:', ":1:9: unknown label 'missing'"),
                                 ('GO TO', ':1:6: expected a label'),
                                 ('GOTO 90:', ":1:6: unknown label '90'"),
                                 ('ON 1 GOTO ok, missing\nok:', ":1:15: unknown label 'missing'"),
                                 ('ON 2 GOSUB', ':1:11: expected a label'),
                                 ('ON 1 PRINT', ':1:6: expected GOTO or GOSUB'),
                                 ('GOTO :', ':1:6: expected a label'),
                                 ('GOTO here::\nhere:', ":1:11: unexpected ':'"),
                                 ('RETURN TO missing', 'unknown label'),
                                 ('RETURN TO', 'expected a label'),
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

    def test_last_file_status(self):
        (self.work / 'input').write_bytes(b'abc')
        result = self.run_native(ROOT / 'tests/io/last-file-status.b', ROOT / 'tests/io/file-status-probe.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'], cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'0\nopen\t128\nopened\t0\nread\t128\nlocked\t-2\n'
                                        b'write\t32768\nwrote\t0\t0\nfields\t0\t1\nroutine\t128\n'
                                        b'after call\t128\nMEMORY\t0\nclose\t128\nseq open\t0\nab\t0\n'
                                        b'short\t128\nreadonly\t24576\nseq close\t0\n')

    def test_status_wrong_argument_count(self):
        source = self.work / 'status.b'
        source.write_text('CRT STATUS(1)\n')
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:5: wrong argument count for 'STATUS'", result.stderr)

    def test_record_file_status(self):
        result = self.run_native(ROOT / 'tests/io/file-status.b', options=['--memory-file', 'data/customers'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'0,7,data/customers,MEMORY,24\n[]\n2\n128:[]\n')

    def test_status_empty_descriptor(self):
        source = self.work / 'status.b'
        source.write_text("STATUS INFO FROM '' ELSE STOP\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:1: STATUS requires a nonempty file descriptor'.encode(), result.stderr)

    def test_sequential_file_status(self):
        path = self.work / 'data'
        path.write_bytes(b'one\ntwo\n')
        os.chmod(path, 0o640)
        source = self.work / 'status.b'
        source.write_text("""OPENSEQ 'data' READONLY TO F ELSE STOP
READSEQ V FROM F ELSE STOP
STATUS X FROM F ELSE STOP
CRT X<1>:',':X<2>:',':X<3>:',':X<4>:',':X<5>:',':X<6>
CRT X<7>:',':X<8>:',':X<9>:',':X<10>:',':X<11>:',':X<12>
CRT X<15>:',':X<16>:',':X<17>:',':X<18>:',':X<19>
CRT X<20>
CRT X<21>
READSEQ V FROM F ELSE STOP
READSEQ V FROM F THEN STOP ELSE NULL
STATUS X FROM F ELSE STOP
CRT X<1>:',':X<2>:',':X<4>
CLOSESEQ F
""")
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        st = path.stat()
        identity = [st.st_nlink, st.st_uid, st.st_gid, st.st_ino, st.st_dev, st.st_rdev]
        times = []
        for seconds in (st.st_mtime_ns // 10**9, st.st_ctime_ns // 10**9):
            t = datetime.fromtimestamp(seconds)
            times.extend([t.hour * 3600 + t.minute * 60 + t.second, (t.date() - date(1967, 12, 31)).days])
        self.assertEqual(result.stdout.splitlines(), [
            b'4,0,0,4,640,8', ','.join(map(str, identity)).encode(), ','.join(map(str, times + [0])).encode(),
            os.fsencode(path.resolve()), b'SEQ', b'8,1,0',
        ])

    def test_openpath(self):
        result = self.run_native(ROOT / 'tests/io/openpath.b',
                                 options=['--memory-file', 'data/customers',
                                          '--memory-file', '/records/customers'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'0\nAda\nupdated\nGrace\n128\ndefault cleared\n'
                         b'128\ndescriptor cleared\nno dictionary\n')

    def test_record_file_close(self):
        result = self.run_native(ROOT / 'tests/io/close.b', options=[
            '--memory-file', 'F', '--memory-file', 'G', '--memory-lock', 'F', 'foreign'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'0\t0\t2\t-2\nsaved\n0\t0\t0\nalready closed\nordinary\nsaved\n1\n')

    def test_close_by_reference_retires_local_cleanup(self):
        main = self.work / 'main.b'
        opener = self.work / 'opener.b'
        closer = self.work / 'closer.b'
        main.write_text("OPEN 'F' TO F ELSE STOP\nCALL OPENER(F)\nCRT RECORDLOCKED(F,'id')\n")
        opener.write_text("SUBROUTINE OPENER(F)\nOPEN 'F' TO LOCAL ELSE STOP\n"
                          "CALL CLOSER(LOCAL)\nREADU R FROM F,'id' ELSE NULL\nRETURN\n")
        closer.write_text("SUBROUTINE CLOSER(F)\nCLOSE F\nRETURN\n")
        result = self.run_native(main, opener, closer, options=['--memory-file', 'F'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'2\n')

    def test_putenv(self):
        env = dict(os.environ, JBCC_TEST_PUTENV='inherited')
        env.pop('JBCC_TEST_NEW_ENV', None)
        result = self.run_native(ROOT / 'tests/io/putenv.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'inherited\ntwo words=three\ntwo words=three\n'
                         b'1:1[]\n0:0:0\n1[]\n[]\n1\ntwo words=three\n')

    def test_getenv(self):
        env = dict(os.environ, JBCC_TEST_VALUE='two words', JBCC_TEST_EMPTY='')
        env.pop('JBCC_TEST_ABSENT', None)
        result = self.run_native(ROOT / 'tests/io/getenv.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'two words\ntwo words\n1[]\n0[]\n[]\n1:two words\n'
                         b'JBCC_TEST_VALUE:1:two words\n0\ntwo words\n')

    def test_open_sections(self):
        run = self.run_native(ROOT / 'tests/io/open-sections.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-dict', 'CUSTOMERS',
                                       '--memory-file', 'DATA.ONLY', '--memory-dict', 'DICT.ONLY'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'data\ndefinition\nremoved from dictionary\ndata\n'
                                     b'missing dictionary\ndescriptor cleared\nmissing data file\n')
        self.assertEqual(run.stderr, b'')

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

    def test_readu(self):
        run = self.run_native(ROOT / 'tests/io/readu.b', ROOT / 'tests/io/reopen.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'128\t2\n0\nfirst\t2\nown lock\n0\n0\t2\n0\n0\n0\n'
                                     b'0\t-2\nbusy\t-2\tkept\nerror\t32768\n'
                                     b'write conflict\t32768\ndelete conflict\t32768\n-2\n')
        self.assertEqual(run.stderr, b'')

    def test_readu_unhandled_fixture_conflict(self):
        source = self.work / 'locked.b'
        source.write_text("OPEN 'F' ELSE STOP\nREADU R FROM 'busy' ELSE STOP\n")
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:2:1: READU cannot wait for a simulated foreign lock'.encode(), run.stderr)

    def test_recordlocku_reserves_key_and_reports_contention(self):
        source = self.work / 'recordlocku.b'
        source.write_text("""OPEN 'F' TO F ELSE STOP
OPEN 'F' ELSE STOP
RECORDLOCKU 'new'
RECORDLOCKU F, 'new' SETTING S THEN CRT '[':S:']' ELSE STOP
CRT RECORDLOCKED(F, 'new')
READ R FROM F, 'new' THEN STOP ELSE CRT 'absent'
RECORDLOCKU F, 'busy' SETTING S LOCKED CRT S:':':SYSTEM(1036)
BAD = ''
RECORDLOCKU BAD, 'new' SETTING S ON ERROR CRT S
RELEASE F, 'new'
CRT RECORDLOCKED(F, 'new'):':':RECORDLOCKED(F, 'busy')
""")
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'[]\n2\nabsent\n-2:1\n32768\n0:-2\n')
        self.assertEqual(run.stderr, b'')

    def test_recordlocku_unhandled_contention_reports_call_site(self):
        source = self.work / 'recordlocku.b'
        source.write_text("OPEN 'F' ELSE STOP\nRECORDLOCKU 'busy'\n")
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:2:1: RECORDLOCKU cannot wait for a simulated foreign lock'.encode(),
                      run.stderr)

    def test_assign_system_resets_blocked_record_lock_counter(self):
        source = self.work / 'assign-system.b'
        source.write_text("""OPEN 'F' TO F ELSE STOP
Key = 1036
CRT SYSTEM(Key)
FOR I = 1 TO 2
    READU R FROM F, 'busy' LOCKED NULL THEN STOP ELSE STOP
NEXT I
CRT SYSTEM(Key)
ASSIGN 0 TO SYSTEM(Key)
CRT SYSTEM(Key)
CRT RECORDLOCKED(F, 'busy')
""")
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\n2\n0\n-2\n')
        self.assertEqual(run.stderr, b'')

    def test_assign_system_diagnostics(self):
        source = self.work / 'assign-system.b'
        for statement, diagnostic in [
                ('ASSIGN 1 TO SYSTEM(1036)', 'SYSTEM(1036) can only be reset to zero'),
                ('ASSIGN 7 TO SYSTEM(1039)', 'ASSIGN TO SYSTEM(1039) requires a journaling backend'),
                ('ASSIGN 0 TO SYSTEM(2021)', 'unsupported ASSIGN TO SYSTEM key 2021')]:
            with self.subTest(statement=statement):
                source.write_text(statement + '\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:1: {diagnostic}'.encode(), run.stderr)

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

    def test_readvu(self):
        run = self.run_native(ROOT / 'tests/io/readvu.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'second|value\t0\t2\nkey\n0\t2\n0\n128\t0\t2\n0\n'
                                     b'-2\tkept\nfirst\t0\n32768\t0\n')
        self.assertEqual(run.stderr, b'')

    def test_readvu_diagnostics(self):
        source = self.work / 'readvu.b'
        for field, diagnostic in [("'bad'", 'requires a numeric field number'),
                                  ('1', 'cannot wait for a simulated foreign lock')]:
            with self.subTest(field=field):
                source.write_text(f"OPEN 'F' ELSE STOP\nREADVU R FROM 'busy',{field} ELSE STOP\n")
                run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:2:1: READVU {diagnostic}'.encode(), run.stderr)

    def test_write_setting_and_on_error(self):
        result = self.run_native(ROOT / 'tests/io/write-error.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'0\t0\ninserted\nthen\nelse\n32768\t-2\n'
                                        b'no record\nbad 128\n128\nupdated\n')

    def test_write_on_error_diagnostics(self):
        source = self.work / 'write.b'
        source.write_text("WRITE 'value' TO 'key' ON NULL\n")
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:27: expected 'ERROR'", result.stderr)
        source.write_text("WRITE 'value' TO 'key'\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: WRITE failed'.encode(), run.stderr)

    def test_writeu(self):
        result = self.run_native(ROOT / 'tests/io/writeu.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'second\t0\t2\nupdated\t2\n0\n0\n0\n32768\t-2\n'
                                        b'no record created\n128\nbad descriptor\nordinary write\n')

    def test_writeu_unhandled_failure(self):
        source = self.work / 'writeu.b'
        source.write_text("WRITEU 'value' TO 'key'\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:1: WRITEU failed'.encode(), result.stderr)

    def test_writev_and_writevu(self):
        result = self.run_native(ROOT / 'tests/io/writev.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'0\t2\n0\none|two,extra|three|||six\n||new\n0\n'
                                        b'32768\t-2\n32768\nmissing\n128\n')

    def test_writev_field_number_diagnostics(self):
        source = self.work / 'writev.b'
        for op, field in [('WRITEV', "'bad'"), ('WRITEVU', '0'), ('WRITEV', '1.5'), ('WRITEVU', '-1')]:
            with self.subTest(op=op, field=field):
                source.write_text(f"{op} 'value' TO 'key',{field}\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:1:1: {op} requires a positive integer field number'.encode(),
                              result.stderr)

    def test_inmat_dimensions_and_latest_load(self):
        result = self.run_native(ROOT / 'tests/io/inmat.b', ROOT / 'tests/io/inmat-shape.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'0\t3\t2x4\n3\t0\n0\t4\tc|d\n3\t2\n0\n0\n'
                                        b'2\t2\n0\t2\tz\n2\t2\n2x4\n1\n')

    def test_inmat_requires_a_matrix_argument(self):
        source = self.work / 'inmat.b'
        source.write_text("X = 1\nCRT INMAT(X)\n")
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:2:11: expected a dimensioned array 'X'", result.stderr)

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

    def test_matreadu(self):
        run = self.run_native(ROOT / 'tests/io/matreadu.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'3\tone\ttwo|three\t2\nupdated\t0\nmissing\t128\tupdated\t2\n'
                                     b'0\nlocked\t-2\tupdated\ttwo|three\nerror\t32768\tupdated\n')
        self.assertEqual(run.stderr, b'')

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

    def test_sselect_file(self):
        result = self.run_native(ROOT / 'tests/io/sselect.b', options=['--memory-file', 'F'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, b'missing default\n128\nempty\n0\ndefault item1\n'
                                        b'numbered item1\nitem1\nitem10\nitem2\nbad file 128\ncleared\n')

    def test_sselect_diagnostics(self):
        source = self.work / 'sselect.b'
        source.write_text("SSELECT TO 11\n")
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:12: select list number must be between 0 and 10", result.stderr)
        source.write_text("SSELECT\n")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:1:1: SSELECT failed".encode(), run.stderr)

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
                                      'X = F(X)\nIF X THEN CALL S(X)\nCALL @X(X)\n')
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

    def test_ascii_and_ebcdic(self):
        (self.work / 'hello').write_bytes(bytes.fromhex('c8 85 93 93 96 40 91 c2 c3'))
        data = bytes(range(1, 256))
        (self.work / 'bytes').write_bytes(data)
        result = self.run_native(ROOT / 'tests/io/ebcdic.b', cwd=self.work)
        expected = (b'Hello jBC\n' + data.decode('cp037').encode('latin-1')
                    + data.decode('latin-1').encode('cp037') + data + data + b'0\t0\n')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, b''))

    def test_ascii_and_ebcdic_argument_counts(self):
        source = self.work / 'invalid.b'
        for call, name in [('ASCII()', 'ASCII'), ("EBCDIC('a','b')", 'EBCDIC')]:
            with self.subTest(call=call):
                source.write_text(f'CRT {call}\n')
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f"{source}:1:5: wrong argument count for '{name}'", result.stderr)

    def test_seq_reads_block_bytes(self):
        source = self.work / 'decode.b'
        (self.work / 'input').write_bytes(b'\x01\xfeAB')
        source.write_text("""OPENSEQ 'input' READONLY TO F ELSE ABORT
READBLK Block FROM F,4 ELSE ABORT
CRT SEQ(Block[1,1]) * 256 + SEQ(Block[2,1]), SEQ(Block[3,2])
CLOSESEQ F
""")
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'510\t65\n', b''))

    def test_seqx_resolves_as_external_function(self):
        source = self.work / 'main.b'
        function = self.work / 'seqx.b'
        source.write_text("DEFFUN SEQX(S)\nCRT SEQX('b'), SEQ('b')\n")
        function.write_text("FUNCTION SEQX(S)\nRETURN INDEX('abc',S,1)\n")
        result = self.run_native(source, function)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'2\t98\n', b''))

    def test_seq_wrong_argument_count(self):
        source = self.work / 'invalid.b'
        source.write_text("CRT SEQ('a','b')\n")
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f"{source}:1:5: wrong argument count for 'SEQ'", result.stderr)

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

    def test_repeated_include_reuses_common_matrix_slots(self):
        main = self.work / 'main.b'
        sub = self.work / 'check.b'
        include = self.work / 'shared.inc'
        include.write_text("COMMON /SHARED/ Rows(N,2), Fixed(2), Tail\nCount += 1\n")
        main.write_text("""N = 3
Count = 0
$INSERT shared.inc
Rows(3,2) = 'row'
Fixed(2) = 'fixed'
Tail = 'tail'
$INSERT shared.inc
CALL CHECK()
CRT Rows(3,2):':':Fixed(2):':':Tail:':':Count
""")
        sub.write_text("""SUBROUTINE CHECK()
COMMON /SHARED/ A(3,2), B(2), C
A(3,2) := '!'
B(2) := '!'
C := '!'
""")
        result = self.run_native(main, sub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, b'row!:fixed!:tail!:2\n')
        self.assertEqual(result.stderr, b'')

    def test_repeated_common_matrix_rejects_incompatible_dimensions(self):
        source = self.work / 'bad.b'
        source.write_text("COMMON /X/ A(2,3)\nCOMMON /X/ A(3,2)\n")
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:2:12: incompatible COMMON matrix dimensions'.encode(), result.stderr)

        for first in ("COMMON /X/ A(N,3)", "IF 0 THEN COMMON /X/ A(N,3)"):
            with self.subTest(first=first):
                source.write_text(f"N = 2\n{first}\nN = 2\nCOMMON /X/ A(3,N)\n")
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}:4:12: incompatible COMMON matrix dimensions'.encode(), result.stderr)

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
Out = REMOVE(Arg,D)
IF D EQ 0 THEN
  Shared = Shared
  REMOVE Out FROM Arg SETTING D
END
""")
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'first\nlast\t0\nfirst\n')

    def test_remove_expression_diagnostics(self):
        source = self.work / 'bad.b'
        for statement, message in [
            ('CRT REMOVE(Missing,D)', ":1:12: unassigned variable 'Missing'"),
            ("CRT REMOVE('a',1)", ':1:16: expected a name'),
        ]:
            with self.subTest(statement=statement):
                source.write_text(statement + '\n')
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(source) + message, result.stderr)

    def test_matrix_assignment_diagnostics(self):
        source = self.work / 'main.b'
        source.write_text('DIM A(2), B(2)\nB(0) = 0\nMAT A = MAT B\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:3:13: unassigned element in matrix 'B'".encode(), run.stderr)
        source.write_text('DIM A(1), B(2)\nB(0) = 0\nB(1) = 1\nMAT A = MAT B\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f"{source}:4:13: unassigned element in matrix 'B'".encode(), run.stderr)

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

    def test_cursor_coordinate_diagnostics(self):
        source = self.work / 'cursor.b'
        for args, message in [("0, 'x'", 'expected a numeric value'),
                              ('-1, 0', 'negative cursor coordinate'),
                              ('0, -1', 'negative cursor coordinate'),
                              ('-3.5', 'unsupported one-argument @ code'),
                              ('-5', 'unsupported one-argument @ code')]:
            with self.subTest(args=args):
                source.write_text(f'CRT @({args})\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: {message}'.encode(), run.stderr)

    def test_invocation_sentence(self):
        source = self.work / 'caller.b'
        routine = ROOT / 'tests/routines/get.sentence.b'
        binary = self.work / 'invocation'
        for direct_read in (False, True):
            source.write_text(('CRT @SENTENCE<1>\n' if direct_read else '') +
                              'CALL GET.SENTENCE(S, A)\nCRT S\nCRT A\n')
            subprocess.run([CLI, '--exe', routine, source, '-o', binary], check=True)
            for args, sentence, first in [
                    ([], b'./invocation', b''),
                    (['42', 'two words', '', 'last'], b'./invocation 42 two words  last', b'42')]:
                with self.subTest(direct_read=direct_read, args=args):
                    run = subprocess.run(['./invocation', *args], cwd=self.work, capture_output=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    self.assertEqual(run.stdout, (sentence + b'\n') * (1 + direct_read) + first + b'\n')

    def test_input_from_pipe(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input.b', '-o', binary], check=True)
        first = b'  ' + b'x' * 512 + b'  '
        run = subprocess.run([binary], input=first + b'\n\nlast', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'?"' + first + b'"\nline2> ""\n"last"\n""\n')
        run = subprocess.run([binary], input=b'a\0b\n', capture_output=True, timeout=5)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(b'input.b:2:1: INPUT cannot store a NUL byte', run.stderr)

    def test_length_limited_input_from_pipe(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input-limit.b', '-o', binary], check=True)
        run = subprocess.run([binary], input=b'abcde\nx\nend', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'abc|de||x||end\n')

    def test_inputclear_discards_only_terminal_typeahead(self):
        source = self.work / 'input.b'
        binary = self.work / 'input'

        def read_until(fd, marker):
            data = bytearray()
            while not data.endswith(marker):
                self.assertTrue(select.select([fd], [], [], 5)[0], data)
                data.extend(os.read(fd, 1024))
            return bytes(data)

        for statement in ('INPUTCLEAR', 'CLEARINPUT'):
            with self.subTest(statement=statement):
                source.write_text(f"""PROMPT ''
DATA 'queued'
{statement}
INPUT Queued
CRT Queued
PROMPT '>'
INPUT Fresh
CRT Fresh
""")
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
                run = subprocess.run([binary], input=b'pipe\n', capture_output=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, b'queued\n>pipe\n')
                self.assertEqual(run.stderr, b'')

                master, slave = os.openpty()
                self.addCleanup(os.close, master)
                self.addCleanup(os.close, slave)
                mode = termios.tcgetattr(slave)
                mode[3] &= ~(termios.ECHO | termios.ECHONL)
                termios.tcsetattr(slave, termios.TCSANOW, mode)
                os.write(master, b'stale\npartial')
                self.assertTrue(select.select([slave], [], [], 5)[0])
                with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
                    try:
                        self.assertEqual(read_until(master, b'>'), b'queued\r\n>')
                        os.write(master, b'fresh\n')
                        self.assertEqual(read_until(master, b'\r\n'), b'fresh\r\n')
                        self.assertEqual(proc.wait(timeout=5), 0)
                    finally:
                        if proc.poll() is None:
                            proc.kill()

    def test_input_underscore_discards_excess_in_queue_and_pipe(self):
        source = self.work / 'input.b'
        source.write_text("""PROMPT ''
DATA 'queued':@FM:'next'
INPUT A, 2_
INPUT B
INPUT C, 1_:
INPUT D, 1:_
INPUT E
CRT A:'|':B:'|':C:'|':D:'|':E
""")
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        run = subprocess.run([binary], input=b'first\nsecond\nlast', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'qu|next|f|s|last\n')
        self.assertEqual(run.stderr, b'')

    def test_input_underscore_rings_bell_and_waits_for_enter(self):
        source = self.work / 'input.b'
        source.write_text("PROMPT '>'\nINPUT X,1_:\nCRT '[':X:']'\n")
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)

        def read_until(marker):
            data = bytearray()
            while not data.endswith(marker):
                self.assertTrue(select.select([master], [], [], 5)[0], data)
                data.extend(os.read(master, 1024))
            return bytes(data)

        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
            try:
                self.assertEqual(read_until(b'>'), b'>')
                os.write(master, b'ab')
                self.assertEqual(read_until(b'\a'), b'a\a')
                os.write(master, b'\n')
                self.assertEqual(read_until(b'\r\n'), b'[a]\r\n')
                self.assertEqual(proc.wait(timeout=5), 0)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_plain_execute_and_perform(self):
        run = self.run_native(ROOT / 'tests/programs/execute.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'before\nchild\nsecond\nafter\n')
        self.assertEqual(run.stderr, b'stderr\n')

    def test_capturing(self):
        run = self.run_native(ROOT / 'tests/programs/capturing.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'one\xfe\xfethree\xfe\nunterminated\n[]\n')
        self.assertEqual(run.stderr, b'diagnostic\n')

    def test_capture_from_pipe(self):
        source = self.work / 'capture.b'
        source.write_text("EXECUTE 'cat' CAPTURING Output\nCRT Output:\n")
        binary = self.work / 'capture'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        payload = b'x' * (256 * 1024) + b'\r\n\xff'
        run = subprocess.run([binary], input=payload, capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, payload.replace(b'\n', b'\xfe'))
        run = subprocess.run([binary], input=b'one\x00two', capture_output=True, timeout=5)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: CAPTURING cannot store a NUL byte'.encode(), run.stderr)

    def test_execute_returning_and_setting(self):
        run = self.run_native(ROOT / 'tests/programs/returning.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        status = b'7\xfebad\xfeworse\xfe\n'
        captured = b'one\xfetwo\n'
        self.assertEqual(run.stdout, captured + status + status + captured + b'visible\n5\n0\n2\n143\n')
        self.assertEqual(run.stderr, b'')

    def test_execute_large_stdout_and_stderr(self):
        source = self.work / 'execute.b'
        source.write_text("""EXECUTE "awk 'BEGIN {for(i=0;i<65536;i++) print 1}' >&2; cat" RETURNING R CAPTURING O
CRT R
CRT O:
""")
        binary = self.work / 'execute'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        payload = b'x' * (256 * 1024)
        run = subprocess.run([binary], input=payload, timeout=5, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'0\xfe' + b'1\xfe' * 65536 + b'\n' + payload)
        self.assertEqual(run.stderr, b'')

    def test_execute_result_diagnostics(self):
        source = self.work / 'execute.b'
        for clauses, repeated in [('SETTING A RETURNING B', 'RETURNING'),
                                  ('CAPTURING A CAPTURING B', 'CAPTURING')]:
            source.write_text(f"EXECUTE ':' {clauses}\n")
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
            column = source.read_text().rindex(repeated) + 1
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(f'{source}:1:{column}: duplicate {repeated} clause'.encode(), run.stderr)
        source.write_text("""EXECUTE "printf '\\000' >&2" SETTING R\n""")
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: RETURNING cannot store a NUL byte'.encode(), run.stderr)

    def test_execute_child_program(self):
        child = self.work / 'child.b'
        child.write_text("PROMPT ''\nINPUT value\nCRT 'child read ' : value\nEXIT(4)\n")
        subprocess.run([CLI, '--exe', child, '-o', self.work / 'child'], check=True)
        main = self.work / 'main.b'
        main.write_text("CALL RUN.CHILD()\nCRT 'returned ' : @SYSTEM.RETURN.CODE\n")
        sub = self.work / 'sub.b'
        sub.write_text("SUBROUTINE RUN.CHILD()\nPERFORM './child'\n")
        binary = self.work / 'main'
        subprocess.run([CLI, '--exe', main, sub, '-o', binary], check=True)
        run = subprocess.run([binary], cwd=self.work, input=b'hello\n', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, b'child read hello\nreturned 4\n')
        self.assertEqual(run.stderr, b'')

    def test_execute_command_diagnostics(self):
        source = self.work / 'command.b'
        for command, message in [("CHAR(255) : 'ktrue'", 'unsupported EXECUTE shell selector'),
                                 ("'true' : @FM : 'true'", 'field-mark-separated EXECUTE commands are unsupported')]:
            with self.subTest(command=command):
                source.write_text(f'EXECUTE {command}\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:1: {message}'.encode(), run.stderr)

    def test_matchfield_invalid_field(self):
        source = self.work / 'matchfield.b'
        for field in ("''", "'two'", '1.5'):
            with self.subTest(field=field):
                source.write_text(f"CRT MATCHFIELD('12', '2N', {field})\n")
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:5: MATCHFIELD requires an integer field number'.encode(), run.stderr)

    def test_sleep_duration_and_default(self):
        source = ROOT / 'tests/programs/sleep.b'
        binary = self.work / 'pause'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        for args, minimum in [([], 1.0), (['.15'], 0.15), (['0'], 0)]:
            with self.subTest(args=args):
                start = time.monotonic()
                run = subprocess.run(['pause', *args], executable=binary, capture_output=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertGreaterEqual(time.monotonic() - start, minimum)
                self.assertEqual(run.stdout, b'awake\n')
        for value, message in [('-0.1', 'nonnegative duration'), ('later', 'nonnegative duration'),
                               ('08:30', 'clock time is unsupported')]:
            with self.subTest(value=value):
                run = subprocess.run(['pause', value], executable=binary, capture_output=True, timeout=5)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:2:34: SLEEP'.encode(), run.stderr)
                self.assertIn(message.encode(), run.stderr)

    def test_timed_input_restarts_after_each_byte(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input-timeout.b', '-o', binary], check=True)
        for data in (b'x\n', b'x'):
            run = subprocess.run([binary], input=data, capture_output=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, b'?complete [x]\n')
        with subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.read(1), b'?')
                for byte in (b'a', b'b', b'c'):
                    proc.stdin.write(byte)
                    proc.stdin.flush()
                    if byte != b'c':
                        time.sleep(0.6)
                self.assertEqual(proc.wait(timeout=5), 0)
                self.assertEqual(proc.stdout.read(), b'complete [abc]\n')
            finally:
                proc.kill()

    def test_timed_input_diagnostics(self):
        source = self.work / 'input.b'
        source.write_text('INPUT X FOR 2\n')
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:14: expected THEN or ELSE'.encode(), run.stderr)
        source.write_text('INPUT X FOR -1 ELSE CRT X\n')
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(f'{source}:1:1: negative INPUT timeout'.encode(), run.stderr)

    def test_input_length_diagnostics(self):
        source = self.work / 'input.b'
        for limit, message in [('-1', 'negative INPUT length'), ("'x'", 'expected a numeric value')]:
            with self.subTest(limit=limit):
                source.write_text(f'INPUT X, {limit}\n')
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(f'{source}:1:1: {message}'.encode(), run.stderr)

    def test_hush_nonnumeric_operand(self):
        source = self.work / 'invalid.b'
        source.write_text("HUSH 'bad'\n")
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(f'{source}:1:1: HUSH requires a numeric operand'.encode(), result.stderr)

    def test_echo_controls_terminal_input_and_system24(self):
        source = self.work / 'echo.b'
        source.write_text("""PROMPT '>'
CRT SYSTEM(24)
ECHO OFF
CRT SYSTEM(24)
INPUT Secret
CRT LEN(Secret)
ECHO 2 > 1
HUSH ON
Quiet = SYSTEM(24)
HUSH OFF
CRT Quiet:':':SYSTEM(24)
INPUT Visible
ECHO ON
CRT SYSTEM(24)
ECHO 0
CRT SYSTEM(24)
""")
        binary = self.work / 'echo'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)

        def read_until(marker):
            data = bytearray()
            while not data.endswith(marker):
                self.assertTrue(select.select([master], [], [], 5)[0], data)
                data.extend(os.read(master, 1024))
            return bytes(data)

        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
            try:
                self.assertEqual(read_until(b'>'), b'1\r\n0\r\n>')
                os.write(master, b'secret\n')
                self.assertEqual(read_until(b'>'), b'6\r\n0:1\r\n>')
                os.write(master, b'visible\n')
                self.assertEqual(read_until(b'1\r\n0\r\n'), b'visible\r\n1\r\n0\r\n')
                self.assertEqual(proc.wait(timeout=5), 0)
                actual = termios.tcgetattr(slave)
                actual[3] &= ~getattr(termios, 'PENDIN', 0)
                self.assertEqual(actual, original)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_hush_terminal_input_and_printer(self):
        source = self.work / 'hush.b'
        source.write_text("HUSH ON\nPRINT ON 1 'job'\nINPUT X\nHUSH OFF\nCRT LEN(X)\nINPUT Y\nCRT Y\n")
        binary = self.work / 'hush'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        env = dict(os.environ, JBCC_PRINT_DIR=str(self.work))
        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave, env=env) as proc:
            try:
                deadline = time.monotonic() + 5
                while termios.tcgetattr(slave)[3] & termios.ECHO:
                    self.assertLess(time.monotonic(), deadline, 'INPUT did not disable echo')
                    time.sleep(0.01)
                os.write(master, b'secret\n')
                output = bytearray()
                while not output.endswith(b'?'):
                    self.assertTrue(select.select([master], [], [], 5)[0], output)
                    output.extend(os.read(master, 1024))
                self.assertEqual(output, b'6\r\n?')
                self.assertTrue(termios.tcgetattr(slave)[3] & termios.ECHO)
                os.write(master, b'ok\n')
                self.assertEqual(proc.wait(timeout=5), 0)
            finally:
                proc.kill()
        self.assertEqual([p.read_bytes() for p in self.work.glob('unit-1-*')], [b'job\n'])

    def test_input_terminal_echo(self):
        source = self.work / 'input.b'
        source.write_text("INPUT X:\nCRT '[' : X : ']'\nINPUT X\nCRT X\n"
                          "INPUT X, 2\nCRT X\nINPUT X, 1:\nCRT X\n"
                          "INPUT X FOR 4 ELSE CRT '[' : X : ']'\n"
                          "INPUT X FOR 0 THEN CRT 'unexpected' ELSE CRT DQUOTE(X)\n")
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)

        def check_mode_restored():
            actual = termios.tcgetattr(slave)
            # BSD may set the line discipline's pending-input flag on restore.
            actual[3] &= ~getattr(termios, 'PENDIN', 0)
            self.assertEqual(actual, original)

        def read_until(marker):
            data = bytearray()
            while not data.endswith(marker):
                self.assertTrue(select.select([master], [], [], 5)[0], data)
                data.extend(os.read(master, 1024))
            return bytes(data)

        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
            try:
                self.assertEqual(read_until(b'?'), b'?')
                os.write(master, b'ax')
                self.assertEqual(read_until(b'x'), b'ax')
                os.write(master, original[6][termios.VERASE] + b'b\n')
                self.assertEqual(read_until(b'?'), b'\b \bb[ab]\r\n?')
                os.write(master, b'c\n')
                self.assertEqual(read_until(b'?'), b'c\r\nc\r\n?')
                os.write(master, b'xy')
                self.assertEqual(read_until(b'?'), b'xy\r\nxy\r\n?')
                os.write(master, b'z')
                self.assertEqual(read_until(b'?'), b'zz\r\n?')
                os.write(master, b'ab')
                self.assertEqual(proc.wait(timeout=5), 0)
                self.assertEqual(read_until(b'""\r\n'), b'ab[ab]\r\n?""\r\n')
                check_mode_restored()
            finally:
                proc.kill()

        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
            try:
                self.assertEqual(read_until(b'?'), b'?')
                proc.terminate()
                proc.wait(timeout=5)
                check_mode_restored()
            finally:
                proc.kill()

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
        source.write_text("""PROMPT ''
CRT SYSTEM(14)
DATA '123', '456'
CRT SYSTEM(14)
CRT SYSTEM(14)
INPUT First, 2
CRT First:':':SYSTEM(14)
CLEARDATA
CRT SYSTEM(14)
""")
        binary = self.work / 'pending'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        with open(os.devnull, 'rb') as empty:
            result = subprocess.run([binary], stdin=empty, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'0\n8\n8\n12:6\n0\n', b''))
        # Preload the pipe before starting the program. Polling leaves its bytes queued.
        read_fd, write_fd = os.pipe()
        with os.fdopen(write_fd, 'wb') as writer:
            writer.write(b'abc')
        with os.fdopen(read_fd, 'rb') as reader:
            result = subprocess.run([binary], stdin=reader, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, b'3\n11\n11\n12:9\n3\n', b''))

    def test_account_path_uses_working_directory(self):
        source = self.work / 'path.b'
        source.write_text('CRT @PATH\n')
        cwd = self.work.joinpath(*(['directory-' + 'x' * 60] * 4))
        cwd.mkdir(parents=True)
        env = dict(os.environ, HOME='/unused-home', PWD='/unused-pwd')
        result = self.run_native(source, env=env, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, os.fsencode(cwd.resolve()) + b'\n')
        self.assertEqual(result.stderr, b'')

    def test_terminal_type_aliases_follow_term(self):
        source = self.work / 'terminal.b'
        source.write_text("""CRT '[':@TERM.TYPE:'] [':@TERM_TYPE:'] [':@TERMTYPE:']'
Changed = PUTENV('TERM=vt220')
CRT Changed:':':@TERM.TYPE:':':@TERM_TYPE:':':@TERMTYPE
""")
        for term in ('xterm-256color', '', None):
            with self.subTest(term=term):
                env = dict(os.environ)
                if term is None:
                    env.pop('TERM', None)
                else:
                    env['TERM'] = term
                result = self.run_native(source, env=env)
                self.assertEqual(result.returncode, 0, result.stderr)
                name = term or ''
                self.assertEqual(result.stdout, f'[{name}] [{name}] [{name}]\n1:vt220:vt220:vt220\n'.encode())
                self.assertEqual(result.stderr, b'')

    def test_tty_name_with_terminal_and_redirected_input(self):
        source = self.work / 'tty.b'
        source.write_text("CRT '[':@TTY:']'\nCRT @TTY[1,1]\n")
        binary = self.work / 'tty'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)

        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        terminal = os.fsencode(os.ttyname(slave))
        for stdin, expected in ((slave, terminal), (subprocess.DEVNULL, b'phantom')):
            with self.subTest(stdin=stdin):
                run = subprocess.run([binary], stdin=stdin, capture_output=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, b'[' + expected + b']\n' + expected[:1] + b'\n')
                self.assertEqual(run.stderr, b'')

    def test_port_number_aliases_use_startup_environment(self):
        main = self.work / 'main.b'
        routine = self.work / 'show.port.b'
        main.write_text('CALL SHOW.PORT()\n')
        routine.write_text("""SUBROUTINE SHOW.PORT()
Changed = PUTENV('JBCPORTNO=99')
Code = 18
CRT Changed:':':@USERNO:':':@USER.NO:':':@USER_NO:':':@UDTNO:':':SYSTEM(Code)
""")
        for setting, port in [('00042', '42'), ('0', '0')]:
            with self.subTest(setting=setting):
                run = self.run_native(main, routine, env=dict(os.environ, JBCPORTNO=setting))
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, (':'.join(['1'] + [port] * 5) + '\n').encode())
                self.assertEqual(run.stderr, b'')

    def test_pid_uses_native_process_id_with_port_override(self):
        source = self.work / 'pid.b'
        source.write_text("CRT @PID\nCRT @USERNO\n")
        binary = self.work / 'pid'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        with subprocess.Popen([binary], env=dict(os.environ, JBCPORTNO='0'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 0, stderr)
            self.assertEqual(stdout, f'{proc.pid}\n0\n'.encode())
            self.assertEqual(stderr, b'')

    def test_port_number_defaults_to_process_id(self):
        source = self.work / 'port.b'
        source.write_text('CRT @USERNO\nCRT @USER.NO\n')
        binary = self.work / 'port'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        env = dict(os.environ)
        env.pop('JBCPORTNO', None)
        for empty in (False, True):
            with self.subTest(empty=empty):
                if empty:
                    env['JBCPORTNO'] = ''
                with subprocess.Popen([binary], env=env, stdout=subprocess.PIPE,
                                      stderr=subprocess.PIPE) as proc:
                    stdout, stderr = proc.communicate(timeout=5)
                    self.assertEqual(proc.returncode, 0, stderr)
                    self.assertEqual(stdout, f'{proc.pid}\n{proc.pid}\n'.encode())
                    self.assertEqual(stderr, b'')

    def test_invalid_port_number_reports_call_site(self):
        source = self.work / 'port.b'
        source.write_text("CRT SYSTEM(17)\nCRT @USERNO\n")
        for setting in ('12-15', '42,43', '-1', '12.25', '9' * 80):
            with self.subTest(setting=setting):
                run = self.run_native(source, env=dict(os.environ, JBCPORTNO=setting))
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, b'0\n')
                self.assertIn(
                    f'{source}:2:5: JBCPORTNO requires a single nonnegative decimal port number'.encode(),
                    run.stderr)

    def test_who_uses_startup_login_name(self):
        main = self.work / 'main.b'
        routine = self.work / 'show.login.b'
        main.write_text('CALL SHOW.LOGIN()\n')
        routine.write_text("""SUBROUTINE SHOW.LOGIN()
Changed = PUTENV('JBCLOGNAME=changed')
CRT Changed:':':@WHO:':':SYSTEM(19)
""")
        for name, legacy, expected in [('MainAccount', 'Fallback', 'MainAccount'),
                                       ('', 'GuideAccount', 'GuideAccount')]:
            with self.subTest(name=name):
                env = dict(os.environ, JBCLOGNAME=name, JBASICLOGNAME=legacy)
                run = self.run_native(main, routine, env=env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, f'1:{expected}:{expected}\n'.encode())
                self.assertEqual(run.stderr, b'')

    def test_who_defaults_to_posix_user_name(self):
        source = self.work / 'who.b'
        source.write_text('CRT @WHO\n')
        env = dict(os.environ, USER='different', LOGNAME='different')
        env.pop('JBCLOGNAME', None)
        env.pop('JBASICLOGNAME', None)
        try:
            expected = os.fsencode(pwd.getpwuid(os.getuid()).pw_name)
        except KeyError:
            expected = b''
        run = self.run_native(source, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected + b'\n')
        self.assertEqual(run.stderr, b'')

    def test_account_aliases_use_startup_account_name(self):
        main = self.work / 'main.b'
        routine = self.work / 'show.account.b'
        main.write_text('CALL SHOW.ACCOUNT()\n')
        routine.write_text("""SUBROUTINE SHOW.ACCOUNT()
Changed = PUTENV('JBCLOGNAME=changed') + PUTENV('LOGNAME=changed')
CRT Changed:':':@LOGNAME:':':@ACCOUNT:':':@WHO
""")
        for override, unix_name, account, login in [
                ('Pseudo', 'Unix', 'Pseudo', 'Pseudo'),
                ('', 'Unix', 'Unix', 'GuideLogin'),
                ('', '', 'GuideLogin', 'GuideLogin')]:
            with self.subTest(override=override, unix_name=unix_name):
                env = dict(os.environ, JBCLOGNAME=override, LOGNAME=unix_name,
                           JBASICLOGNAME='GuideLogin')
                run = self.run_native(main, routine, env=env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, f'2:{account}:{account}:{login}\n'.encode())
                self.assertEqual(run.stderr, b'')

    def test_account_defaults_to_posix_user_name(self):
        source = self.work / 'account.b'
        source.write_text('CRT @LOGNAME\nCRT @ACCOUNT\n')
        env = dict(os.environ)
        for name in ('JBCLOGNAME', 'LOGNAME', 'JBASICLOGNAME'):
            env.pop(name, None)
        try:
            expected = os.fsencode(pwd.getpwuid(os.getuid()).pw_name)
        except KeyError:
            expected = b''
        run = self.run_native(source, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, (expected + b'\n') * 2)
        self.assertEqual(run.stderr, b'')
