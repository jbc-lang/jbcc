import fcntl
import json
import math
import re
import select
import signal
import os
import pwd
import shlex
import struct
import sqlite3
import subprocess
import sys
import tempfile
import termios
import time
import unittest
from datetime import date, datetime, timedelta, timezone
from pathlib import Path


from compiler_support import CLI, ROOT, NativeCompiler, expected_bytes, expected_text


class NativeCompilerTest(unittest.TestCase, NativeCompiler):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        NativeCompiler.__init__(self, Path(tmp.name))


class CompilerTest(NativeCompilerTest):
    def test_heading_terminal_pause(self):
        source = ROOT / 'tests/io/heading-terminal-pause.b'
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
                self.assertIn(expected_bytes('heading-terminal-pause.stdout'), output)
            finally:
                proc.kill()

    def test_lptrhigh_tracks_current_print_destination(self):
        source = ROOT / 'tests/io/lptrhigh-print-destination.b'
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
        expected = expected_bytes('lptrhigh-tracks-current-print-destination.stdout')
        output = bytearray()
        while len(output) < len(expected):
            self.assertTrue(select.select([master], [], [], 5)[0], output)
            output.extend(os.read(master, 1024))
        self.assertEqual(output, expected)

        run = subprocess.run([binary], env=env, capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected_bytes('lptrhigh-tracks-current-print-destination_2.stdout'), b''))
        self.assertEqual([job.read_bytes() for job in self.work.glob('unit-7-*')], [b'24\n'] * 2)

    def test_display_alias_uses_screen_and_crt_formatting(self):
        source = ROOT / 'tests/io/display-screen-formatting.b'
        result = self.run_native(source, env=dict(os.environ, JBCC_PRINT_DIR=str(self.work)))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('display-alias-uses-screen-and-crt-formatting.stdout'), b''))
        self.assertEqual([job.read_bytes() for job in self.work.glob('unit-*-*')], [b'printer\n'])

        source = ROOT / 'tests/io/display-unassigned.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('display-alias-uses-screen-and-crt-formatting.stderr', source=source),
                      result.stderr)

    def test_footing_reserves_rows_and_closes_printer_page(self):
        source = ROOT / 'tests/io/footing-printer-page.b'
        run = self.run_native(source, env=dict(os.environ, JBCC_PRINT_DIR=str(self.work)))
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('footing-reserves-rows-and-closes-printer-page.stdout'))
        job, = self.work.glob('unit-2-*')
        self.assertEqual(job.read_bytes(), b'body\n' + b'\n' * 22 + b'Job    1\n')
        self.assertEqual(run.stderr, b'')

    def test_footing_terminal_pause_and_no_pause(self):
        source = ROOT / 'tests/io/footing-terminal-pause.b'
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
                self.assertEqual(first, expected_bytes('footing-terminal-pause-and-no-pause.stdout'))
                self.assertFalse(select.select([master], [], [], 0.1)[0])
                os.write(master, b'\n')
                self.assertEqual(proc.wait(timeout=5), 0)
                rest = bytearray()
                while not rest.endswith(b'End 3\r\n'):
                    self.assertTrue(select.select([master], [], [], 5)[0], rest)
                    rest.extend(os.read(master, 1024))
                self.assertIn(expected_bytes('footing-terminal-pause-and-no-pause_2.stdout'), rest)
                self.assertTrue(rest.endswith(expected_bytes('footing-terminal-pause-and-no-pause_3.stdout')))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_sequential_block_io(self):
        (self.work / 'input').write_bytes(b'a\r\n\xfeend')
        (self.work / 'binary').write_bytes(b'x\0yz')
        result = self.run_native(ROOT / 'tests/io/block-io.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('sequential-block-io.stdout'))
        self.assertEqual((self.work / 'output').read_bytes(), b'AXB')
        self.assertEqual((self.work / 'input').read_bytes(), b'a\r\n\xfeend')

    def test_block_io_operand_diagnostics(self):
        for fixture_name, message in (
            ('invalid_1.b', expected_text('block-io-operand-diagnostics.stderr')),
            ('invalid_2.b', expected_text('block-io-operand-diagnostics_2.stderr')),
            ('invalid_3.b', expected_text('block-io-operand-diagnostics_2.stderr')),
            ('invalid_4.b', expected_text('block-io-operand-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/block-io-operand-diagnostics' / fixture_name
                result = self.run_native(source, cwd=self.work)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('block-io-operand-diagnostics_4.stderr', source=source, message=message).encode(), result.stderr)

    def test_sequential_create_and_truncate(self):
        (self.work / 'zero').write_bytes(b'old content')
        (self.work / 'input').write_bytes(b'keep\n' + b'discard\n' * 2000)
        result = self.run_native(ROOT / 'tests/io/seq-create.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('sequential-create-and-truncate.stdout'))
        self.assertEqual((self.work / 'new').read_bytes(), b'winner\n')
        self.assertEqual((self.work / 'input').read_bytes(), b'keep\nreplacement\n')
        self.assertEqual((self.work / 'empty').read_bytes(), b'')
        self.assertEqual((self.work / 'zero').read_bytes(), b'')

    def test_create_null_handle(self):
        source = ROOT / 'tests/io/create-null-handle.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('create-null-handle.stderr', source=source).encode(), result.stderr)

    def test_flush_sequential_file(self):
        source = ROOT / 'tests/io/flush-sequential-file.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('flush-sequential-file.stdout'))
        self.assertEqual(result.stderr, b'')

    def test_osopen_access_modes_and_osclose_aliases(self):
        directory = self.work / 'search'
        directory.mkdir()
        data = directory / 'payload'
        data.write_bytes(b'old\nsecond\n')
        source = ROOT / 'tests/io/osopen-access-modes.b'
        result = self.run_native(source, env=dict(os.environ, JEDIFILEPATH=str(directory)), cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('osopen-access-modes-and-osclose-aliases.stdout'), b''))
        self.assertEqual(data.read_bytes(), b'new\nsecond\n')
        self.assertFalse((self.work / 'missing').exists())

    def test_osclose_invalid_handle_reports_location(self):
        source = ROOT / 'tests/io/osclose-invalid-handle.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('osclose-invalid-handle-reports-location.stderr', source=source).encode(), result.stderr)

    def test_osbread_offsets_short_reads_and_nul_conversion(self):
        (self.work / 'data').write_bytes(b'X\0Y\nline\nz')
        source = ROOT / 'tests/io/osbread-offsets.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('osbread-offsets-short-reads-and-nul-conversion.stdout'), b''))

    def test_osbread_error_arms_and_diagnostic(self):
        (self.work / 'data').touch()
        source = ROOT / 'tests/io/osbread-errors.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('osbread-error-arms-and-diagnostic.stdout'))
        self.assertIn(expected_text('osbread-error-arms-and-diagnostic.stderr', source=source).encode(), result.stderr)

    def test_osbwrite_round_trips_bytes_and_advances_cursor(self):
        data = self.work / 'data'
        data.write_bytes(b'0123456789')
        source = ROOT / 'tests/io/osbwrite-offsets.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('osbwrite-round-trips-bytes-and-advances-cursor.stdout'), b''))
        self.assertEqual(data.read_bytes(), b'01A\0BC6Z89\0\0Q')

    def test_osbwrite_error_arms_and_diagnostic(self):
        data = self.work / 'data'
        data.write_bytes(b'unchanged')
        source = ROOT / 'tests/io/osbwrite-errors.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('osbwrite-error-arms-and-diagnostic.stdout'))
        self.assertIn(expected_text('osbwrite-error-arms-and-diagnostic.stderr', source=source).encode(), result.stderr)
        self.assertEqual(data.read_bytes(), b'unchanged')

    def test_oswrite_replaces_appends_and_creates_regular_files(self):
        directory = self.work / 'search'
        directory.mkdir()
        data = directory / 'payload'
        data.write_bytes(b'old contents that should be replaced')
        (self.work / 'empty').write_bytes(b'old')
        source = ROOT / 'tests/io/oswrite-regular-files.b'
        result = self.run_native(source, env=dict(os.environ, JEDIFILEPATH=str(directory)), cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('oswrite-replaces-appends-and-creates-regular-files.stdout'), b''))
        self.assertEqual(data.read_bytes(), b'new\0\ntail')
        self.assertEqual((self.work / 'new').read_bytes(), b'created')
        self.assertEqual((self.work / 'empty').read_bytes(), b'')
        self.assertFalse((self.work / 'payload').exists())

    def test_oswrite_reports_errors_before_truncating_a_locked_file(self):
        data = self.work / 'data'
        data.write_bytes(b'unchanged')
        source = ROOT / 'tests/io/oswrite-lock-errors.b'
        with data.open('rb') as locked:
            fcntl.flock(locked, fcntl.LOCK_EX)
            result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('oswrite-reports-errors-before-truncating-a-locked-file.stdout'))
        self.assertIn(expected_text('oswrite-reports-errors-before-truncating-a-locked-file.stderr', source=source).encode(), result.stderr)
        self.assertEqual(data.read_bytes(), b'unchanged')

    def test_osdelete_path_resolution_and_status(self):
        directory = self.work / 'search'
        directory.mkdir()
        for path in (self.work / 'local', directory / 'local', directory / 'payload',
                     directory / 'explicit', directory / 'search'):
            path.write_bytes(b'data')
        source = ROOT / 'tests/io/osdelete-path-resolution.b'
        search_path = f":{self.work / 'missing'}::{directory}:"
        result = self.run_native(source, cwd=self.work,
                                 env=dict(os.environ, JEDIFILEPATH=search_path))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('osdelete-path-resolution-and-status.stdout'), b''))
        self.assertFalse((self.work / 'local').exists())
        self.assertFalse((directory / 'payload').exists())
        self.assertFalse((directory / 'explicit').exists())
        self.assertEqual((directory / 'local').read_bytes(), b'data')
        self.assertEqual((directory / 'search').read_bytes(), b'data')

    def test_osdelete_missing_file_and_diagnostics(self):
        source = ROOT / 'tests/io/osdelete-missing.b'
        result = self.run_native(source, cwd=self.work,
                                 env=dict(os.environ, JEDIFILEPATH=''))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('osdelete-missing-file-and-diagnostics.stdout'))
        self.assertIn(expected_text('osdelete-missing-file-and-diagnostics.stderr', source=source).encode(), result.stderr)

        source = ROOT / 'tests/io/osdelete-invalid-clause.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('osdelete-missing-file-and-diagnostics_2.stderr', source=source), result.stderr)

    def test_osread_regular_file_and_error_arms(self):
        directory = self.work / 'search'
        directory.mkdir()
        (directory / 'payload').write_bytes(b'a' * 5000 + b'\n\0z\n\n')
        (self.work / 'empty').touch()
        os.mkfifo(self.work / 'fifo')
        source = ROOT / 'tests/io/osread-regular-file.b'
        env = dict(os.environ, JEDIFILEPATH=f'missing-first:{directory}')
        result = self.run_native(source, cwd=self.work, env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('osread-regular-file-and-error-arms.stdout'), b''))

    def test_osread_fatal_error_requires_handler(self):
        source = ROOT / 'tests/io/osread-unhandled-error.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, b'')
        self.assertIn(expected_text('osread-fatal-error-requires-handler.stderr', source=source).encode(), result.stderr)

    def test_nobuf_uses_unbuffered_sequential_io(self):
        data = self.work / 'data'
        data.write_bytes(b'first\nold\n')
        source = ROOT / 'tests/io/nobuf-sequential-file.b'
        binary = self.work / 'nobuf'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        with subprocess.Popen([binary], cwd=self.work, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), expected_bytes('nobuf-uses-unbuffered-sequential-io.stdout'))
                with data.open('r+b') as stream:
                    stream.seek(len(b'first\n'))
                    stream.write(b'new')
                proc.stdin.write(b'continue\n')
                proc.stdin.flush()
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), expected_bytes('nobuf-uses-unbuffered-sequential-io_2.stdout'))
                self.assertEqual(data.read_bytes(), b'first\nnew\nvisible\n')
                stdout, stderr = proc.communicate(b'done\n', timeout=5)
                self.assertEqual((proc.returncode, stdout, stderr), (0, b'', b''))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_nobuf_failure_status_and_diagnostic(self):
        data = self.work / 'data'
        data.write_bytes(b'line\n')
        source = ROOT / 'tests/io/nobuf-errors.b'
        result = self.run_native(source, cwd=self.work)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('nobuf-failure-status-and-diagnostic.stdout'))
        self.assertIn(expected_text('nobuf-failure-status-and-diagnostic.stderr', source=source).encode(), result.stderr)

    def test_timeout_on_regular_sequential_file(self):
        (self.work / 'data').write_bytes(b'line\nblock')
        source = ROOT / 'tests/io/timeout-sequential-file.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('timeout-on-regular-sequential-file.stdout'))
        self.assertEqual(result.stderr, b'')

    def test_timeout_diagnostics(self):
        (self.work / 'data').write_bytes(b'line\n')
        fixtures = ROOT / 'tests/io/timeout-diagnostics'
        for fixture_name, line, message in (
                ('timeout_1.b', 1, expected_text('timeout-diagnostics.stderr')),
                ('timeout_2.b', 2, expected_text('timeout-diagnostics.stderr')),
                ('timeout_3.b', 3, expected_text('timeout-diagnostics.stderr')),
                ('timeout_4.b', 2, expected_text('timeout-diagnostics_2.stderr')),
                ('timeout_5.b', 2, expected_text('timeout-diagnostics_2.stderr')),
                ('timeout_6.b', 2, expected_text('timeout-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = fixtures / fixture_name
                result = self.run_native(source, cwd=self.work)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('timeout-diagnostics_3.stderr', source=source, line=line, message=message).encode(), result.stderr)

    def test_flush_null_handle(self):
        source = ROOT / 'tests/io/flush-null-handle.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('flush-null-handle.stderr', source=source).encode(), result.stderr)

    def test_fileinfo_memory_handle(self):
        source = ROOT / 'tests/io/fileinfo-memory-handle.b'
        run = self.run_native(source, options=['--memory-file', 'customers'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('fileinfo-memory-handle.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_fileinfo_sequential_handle(self):
        source = ROOT / 'tests/io/fileinfo-sequential-handle.b'
        run = self.run_native(source, cwd=self.work)
        self.assertEqual(run.returncode, 0, run.stderr)
        path = os.fsencode(self.work.resolve() / 'report')
        self.assertEqual(run.stdout, expected_bytes('fileinfo-sequential-handle.stdout') + path + expected_bytes('fileinfo-sequential-handle_2.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_fileinfo_unsupported_key(self):
        source = ROOT / 'tests/io/fileinfo-unsupported-key.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('fileinfo-unsupported-key.stderr', source=source).encode(), run.stderr)

    def test_ioctl_filename_returns_text_and_writes_on_success(self):
        source = ROOT / 'tests/io/ioctl-memory-filename.b'
        run = self.run_native(source, options=['--memory-file', 'customers'])
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('ioctl-filename-returns-text-and-writes-on-success.stdout'), b''))

    def test_ioctl_filename_for_sequential_handle(self):
        source = ROOT / 'tests/io/ioctl-sequential-filename.b'
        (self.work / 'report').touch()
        run = self.run_native(source, cwd=self.work)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, os.fsencode(self.work.resolve() / 'report') + expected_bytes('ioctl-filename-for-sequential-handle.stdout'), b''))

    def test_ioctl_unsupported_command_diagnostic(self):
        source = ROOT / 'tests/io/ioctl-unsupported-command.b'
        run = self.run_native(source)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (1, b'', expected_text('ioctl-unsupported-command-diagnostic.stderr', source=source).encode()))

    def test_data_queues_input_and_hands_it_to_commands(self):
        source = ROOT / 'tests/io/data-queued-input.b'
        binary = self.work / 'data'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'fallback\n', capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('data-queues-input-and-hands-it-to-commands.stdout'))
        self.assertEqual(result.stderr, b'')
    def test_sequential_seek(self):
        path = self.work / 'data'
        path.write_bytes(b'abc\n12345\nlast\n')
        result = self.run_native(ROOT / 'tests/io/seek.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('sequential-seek.stdout'))
        self.assertEqual(path.read_bytes(), b'aZ\n\n12345\nlast\nend\n\0\0gap\n')
        self.assertFalse((self.work / 'absent').exists())

    def test_seek_empty_operands(self):
        (self.work / 'data').touch()
        for fixture_name in (
            'invalid_1.b',
            'invalid_2.b',
            'invalid_3.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/seek-empty-operands' / fixture_name
                result = self.run_native(source, cwd=self.work)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('seek-empty-operands.stderr', source=source).encode(), result.stderr)

    def test_sequential_files(self):
        data = b'first\n\n' + b'x' * 1100 + b'\nlast'
        (self.work / 'input').write_bytes(data)
        result = self.run_native(ROOT / 'tests/io/sequential.b', cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('sequential-files.stdout'))
        self.assertEqual((self.work / 'input').read_bytes(), data)
        self.assertEqual((self.work / 'new').read_bytes(), b'one\nTWO\nlast\nend\n')

    def test_sequential_external_lock_and_fifo(self):
        source = ROOT / 'tests/io/openseq-external-lock-and-fifo.b'
        os.mkfifo(self.work / 'pipe')
        with (self.work / 'input').open('wb') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('sequential-external-lock-and-fifo.stdout'))

    def test_opendev_regular_file_and_missing_file(self):
        data = self.work / 'data'
        data.write_bytes(b'first\nsecond\n')
        source = ROOT / 'tests/io/opendev-regular-file.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('opendev-regular-file-and-missing-file.stdout'), b''))
        self.assertEqual(data.read_bytes(), b'first\nchange\n')
        self.assertFalse((self.work / 'missing').exists())

    def test_opendev_lock_fallback_and_fifo(self):
        data = self.work / 'data'
        data.touch()
        os.mkfifo(self.work / 'pipe')
        source = ROOT / 'tests/io/opendev-lock-and-fifo.b'
        with data.open('rb') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('opendev-lock-fallback-and-fifo.stdout'), b''))

        source = ROOT / 'tests/io/opendev-missing-branch.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('opendev-lock-fallback-and-fifo.stderr', source=source), result.stderr)

    def test_ttyget_reads_pseudoterminal_settings(self):
        source = ROOT / 'tests/io/ttyget-settings.b'
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        env = dict(os.environ, JBCC_TEST_PTY=os.ttyname(slave))
        mode = termios.tcgetattr(slave)
        mode[0] = (mode[0] & ~termios.IGNBRK) | termios.BRKINT
        mode[2] = (mode[2] & ~(termios.CSIZE | termios.CSTOPB | termios.PARENB)) | termios.CS8
        mode[3] |= termios.ISIG | termios.ICANON | termios.ECHO
        mode[4] = mode[5] = termios.B9600
        termios.tcsetattr(slave, termios.TCSANOW, mode)
        canonical = self.run_native(source, env=env)
        self.assertEqual((canonical.returncode, canonical.stdout, canonical.stderr),
                         (0, expected_bytes('ttyget-reads-pseudoterminal-settings.stdout'), b''))

        mode[3] &= ~(termios.ICANON | termios.ECHO)
        mode[6][termios.VMIN] = 3
        mode[6][termios.VTIME] = 2
        termios.tcsetattr(slave, termios.TCSANOW, mode)
        noncanonical = self.run_native(source, env=env)
        self.assertEqual((noncanonical.returncode, noncanonical.stdout, noncanonical.stderr),
                         (0, expected_bytes('ttyget-reads-pseudoterminal-settings_2.stdout'), b''))

        source = ROOT / 'tests/io/timeout-terminal-handle.b'
        result = self.run_native(source, env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('ttyget-reads-pseudoterminal-settings.stderr', source=source).encode(),
                      result.stderr)

    def test_ttyget_failure_arms_and_diagnostic(self):
        (self.work / 'data').touch()
        source = ROOT / 'tests/io/ttyget-errors.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('ttyget-failure-arms-and-diagnostic.stdout'), b''))

        source = ROOT / 'tests/io/ttyget-missing-from.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('ttyget-failure-arms-and-diagnostic.stderr', source=source), result.stderr)

    def test_ttyset_round_trip_and_validation(self):
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        mode = termios.tcgetattr(slave)
        mode[2] = (mode[2] & ~(termios.CSIZE | termios.CSTOPB | termios.PARENB)) | termios.CS8
        mode[3] |= termios.ICANON | termios.ECHO
        mode[4] = mode[5] = termios.B9600
        termios.tcsetattr(slave, termios.TCSANOW, mode)
        original = termios.tcgetattr(slave)
        env = dict(os.environ, JBCC_TEST_PTY=os.ttyname(slave))
        source = ROOT / 'tests/io/ttyset-round-trip.b'
        result = self.run_native(source, env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('ttyset-round-trip-and-validation.stdout'), b''))
        restored = termios.tcgetattr(slave)
        local_mask = termios.ICANON | termios.ECHO | termios.ISIG
        self.assertEqual(restored[:3], original[:3])
        self.assertEqual(restored[3] & local_mask, original[3] & local_mask)
        self.assertEqual(restored[4:6], original[4:6])

    def test_ttyset_failure_arms_and_diagnostic(self):
        (self.work / 'data').touch()
        source = ROOT / 'tests/io/ttyset-errors.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('ttyset-failure-arms-and-diagnostic.stdout'), b''))

        source = ROOT / 'tests/io/ttyset-invalid-on.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('ttyset-failure-arms-and-diagnostic.stderr', source=source), result.stderr)

    def test_sequential_routine_lifetime(self):
        (self.work / 'input').write_bytes(b'hello\n')
        source = ROOT / 'tests/routines/sequential-lifetime/main.b'
        sub = ROOT / 'tests/routines/sequential-lifetime/opener.b'
        result = self.run_native(source, sub, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('sequential-routine-lifetime.stdout'))

    def test_saved_lists_across_executables(self):
        directory = self.work / 'lists'
        directory.mkdir()
        env = dict(os.environ, JBCC_LIST_DIR=str(directory))
        written = self.run_native(ROOT / 'tests/io/write-lists.b', options=['--memory-file', 'F'], env=env)
        self.assertEqual((written.returncode, written.stdout, written.stderr), (0, expected_bytes('saved-lists-across-executables.stdout'), b''))
        self.assertFalse((self.work / 'order').exists())
        read = self.run_native(ROOT / 'tests/io/read-lists.b', env=env)
        self.assertEqual((read.returncode, read.stderr), (0, b''))
        self.assertEqual(read.stdout, expected_bytes('saved-lists-across-executables_2.stdout'))

        deleted = self.run_native(ROOT / 'tests/io/delete-lists.b', env=env)
        self.assertEqual((deleted.returncode, deleted.stderr), (0, b''))
        self.assertEqual(deleted.stdout, expected_bytes('saved-lists-across-executables_3.stdout'))
        check = ROOT / 'tests/io/check-deleted-lists.b'
        after = self.run_native(check, env=env)
        self.assertEqual((after.returncode, after.stdout, after.stderr), (0, expected_bytes('saved-lists-across-executables_4.stdout'), b''))

    def test_selected_tracks_default_external_list_across_calls(self):
        main = ROOT / 'tests/routines/selected-list/main.b'
        routine = ROOT / 'tests/routines/selected-list/replace-list.b'
        env = dict(os.environ, JBCC_LIST_DIR=str(self.work))
        run = self.run_native(main, routine, env=env)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('selected-tracks-default-external-list-across-calls.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_cleardata_discards_the_queue_and_preserves_standard_input(self):
        source = ROOT / 'tests/io/cleardata-queued-input.b'
        binary = self.work / 'cleardata'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'pipe\n', capture_output=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('cleardata-discards-the-queue-and-preserves-standard-input.stdout'), b''))

    def test_record_id_survives_loop_collection_and_return(self):
        main = ROOT / 'tests/routines/record-id/main.b'
        routine = ROOT / 'tests/routines/record-id/select-id.b'
        run = self.run_native(main, routine)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('record-id-survives-loop-collection-and-return.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_filename_is_shared_and_independent_of_other_record_context(self):
        main = ROOT / 'tests/routines/record-filename/main.b'
        routine = ROOT / 'tests/routines/record-filename/set-filename.b'
        result = self.run_native(main, routine, options=['--memory-file', 'records'])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('filename-is-shared-and-independent-of-other-record-context.stdout'), b''))

    def test_record_context_survives_collection_and_changes_only_on_explicit_writes(self):
        main = ROOT / 'tests/routines/record-context/main.b'
        routine = ROOT / 'tests/routines/record-context/seed.b'
        run = self.run_native(main, routine, options=['--memory-file', 'records'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('record-context-survives-collection-and-changes-only-on-explicit-writes.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_deletelist_requires_named_store(self):
        source = ROOT / 'tests/io/deletelist-missing-store.b'
        result = self.run_native(source, env=dict(os.environ, JBCC_LIST_DIR=''))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('deletelist-requires-named-store.stderr', source=source).encode(), result.stderr)

    def test_saved_list_write_failure(self):
        source = ROOT / 'tests/io/writelist-missing-directory.b'
        env = dict(os.environ, JBCC_LIST_DIR=str(self.work / 'missing'))
        result = self.run_native(source, env=env)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('saved-list-write-failure.stdout'), b''))

    def test_print_units(self):
        env = dict(os.environ, JBCC_PRINT_DIR=str(self.work))
        result = self.run_native(ROOT / 'tests/io/print-units.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('print-units.stdout'))
        jobs = sorted((p.name.split('-')[1], p.read_bytes()) for p in self.work.glob('unit-*-*'))
        self.assertEqual(jobs, [
            ('0', b'Default 1\nfirst job\n\fDefault 2\n'),
            ('127', b'high\n'),
            ('2', b'Other 1\nA\tB\fOther 9\nseparate\nReset 1\n'),
            ('2', b'new job\n'),
        ])

    def test_report_diagnostics(self):
        for fixture_name, message in (
            ('report_1.b', expected_text('report-diagnostics.stderr')),
            ('report_2.b', expected_text('report-diagnostics.stderr')),
            ('report_3.b', expected_text('report-diagnostics_2.stderr')),
            ('report_4.b', expected_text('report-diagnostics.stderr')),
            ('report_5.b', expected_text('report-diagnostics_3.stderr')),
            ('report_6.b', expected_text('report-diagnostics_4.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/report-diagnostics' / fixture_name
                result = self.run_native(source, env=dict(os.environ, JBCC_PRINT_DIR=''))
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('report-diagnostics_5.stderr', source=source, message=message).encode(), result.stderr)

    def test_date_and_time_in_local_timezone(self):
        source = ROOT / 'tests/programs/date-and-time.b'
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
        source = ROOT / 'tests/programs/timedate-midnight.b'
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
        self.assertEqual(run.stdout, expected_text('timedate-at-local-midnight.stdout'))
        self.assertEqual(run.stderr, '')

    def test_timestamp_returns_utc_seconds_at_current_precision(self):
        source = ROOT / 'tests/programs/timestamp-clock.b'
        clock = ROOT / 'tests/io/timestamp-clock.c'
        binary = self.work / 'timestamp'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        '-Dclock_gettime=test_clock_gettime', self.c, clock, '-o', binary], check=True)
        run = subprocess.run([binary], env=dict(os.environ, TZ='UTC+10'), capture_output=True,
                             text=True, check=True)
        self.assertEqual(run.stdout, expected_text('timestamp-returns-utc-seconds-at-current-precision.stdout'))
        self.assertEqual(run.stderr, '')

    def test_startup_clock_is_shared_across_midnight(self):
        sources = ROOT / 'tests/routines/startup-clock'
        main = sources / 'main.b'
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
        for name, expected in [
                ('date-and-time.b', expected_text('startup-clock-is-shared-across-midnight_2.stdout')),
                ('time-only.b', expected_text('startup-clock-is-shared-across-midnight_3.stdout')),
                ('date-only.b', expected_text('startup-clock-is-shared-across-midnight_4.stdout'))]:
            with self.subTest(source=name):
                routine = sources / name
                subprocess.run([CLI, main, routine, '-o', self.c], check=True)
                subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                                '-Dtime=test_clock', self.c, clock, '-o', binary], check=True)
                run = subprocess.run([binary], env=dict(os.environ, TZ='UTC+1'), capture_output=True,
                                     text=True, check=True)
                self.assertEqual(run.stdout, expected_text('startup-clock-is-shared-across-midnight.stdout') + expected)
                self.assertEqual(run.stderr, '')

    def test_rewind_invalid_channel(self):
        for fixture_name in (
            'rewind_1.b',
            'rewind_2.b',
            'rewind_3.b',
            'rewind_4.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/rewind-invalid-channel' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(expected_text('rewind-invalid-channel.stderr', source=source).encode(),
                              result.stderr)

    def test_readt_invalid_channel(self):
        for fixture_name in (
            'readt_1.b',
            'readt_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/readt-invalid-channel' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(expected_text('readt-invalid-channel.stderr', source=source).encode(),
                              result.stderr)

    def test_writet_diagnostics(self):
        for fixture_name, diagnostic in (
            ('writet_1.b', expected_text('writet-diagnostics.stderr')),
            ('writet_2.b', expected_text('writet-diagnostics.stderr')),
            ('writet_3.b', expected_text('writet-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/writet-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn((str(source) + diagnostic).encode(), result.stderr)

    def test_weof_invalid_channel(self):
        for fixture_name in (
            'weof_1.b',
            'weof_2.b',
            'weof_3.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/weof-invalid-channel' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, b'')
                self.assertIn(expected_text('weof-invalid-channel.stderr', source=source).encode(),
                              result.stderr)

    def test_memory_files(self):
        run = self.run_native(ROOT / 'tests/io/records.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('memory-files.stdout'))

    def test_last_file_status(self):
        (self.work / 'input').write_bytes(b'abc')
        result = self.run_native(ROOT / 'tests/io/last-file-status.b', ROOT / 'tests/io/file-status-probe.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'], cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('last-file-status.stdout'))

    def test_status_wrong_argument_count(self):
        source = ROOT / 'tests/io/status-wrong-argument-count.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('status-wrong-argument-count.stderr', source=source), result.stderr)

    def test_record_file_status(self):
        result = self.run_native(ROOT / 'tests/io/file-status.b', options=['--memory-file', 'data/customers'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('record-file-status.stdout'))

    def test_status_empty_descriptor(self):
        source = ROOT / 'tests/io/status-empty-descriptor.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('status-empty-descriptor.stderr', source=source).encode(), result.stderr)

    def test_sequential_file_status(self):
        path = self.work / 'data'
        path.write_bytes(b'one\ntwo\n')
        os.chmod(path, 0o640)
        source = ROOT / 'tests/io/sequential-file-status.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual(result.returncode, 0, result.stderr)
        st = path.stat()
        identity = [st.st_nlink, st.st_uid, st.st_gid, st.st_ino, st.st_dev, st.st_rdev]
        times = []
        for seconds in (st.st_mtime_ns // 10**9, st.st_ctime_ns // 10**9):
            t = datetime.fromtimestamp(seconds)
            times.extend([t.hour * 3600 + t.minute * 60 + t.second, (t.date() - date(1967, 12, 31)).days])
        self.assertEqual(result.stdout.splitlines(), [
            expected_bytes('sequential-file-status.stdout'), ','.join(map(str, identity)).encode(), ','.join(map(str, times + [0])).encode(),
            os.fsencode(path.resolve()), expected_bytes('sequential-file-status_2.stdout'), expected_bytes('sequential-file-status_3.stdout'),
        ])

    def test_openpath(self):
        result = self.run_native(ROOT / 'tests/io/openpath.b',
                                 options=['--memory-file', 'data/customers',
                                          '--memory-file', '/records/customers'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('openpath.stdout'))

    def test_record_file_close(self):
        result = self.run_native(ROOT / 'tests/io/close.b', options=[
            '--memory-file', 'F', '--memory-file', 'G', '--memory-lock', 'F', 'foreign'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('record-file-close.stdout'))

    def test_close_by_reference_retires_local_cleanup(self):
        main = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/main.b'
        opener = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/opener.b'
        closer = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/closer.b'
        result = self.run_native(main, opener, closer, options=['--memory-file', 'F'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('close-by-reference-retires-local-cleanup.stdout'))

    def test_putenv(self):
        env = dict(os.environ, JBCC_TEST_PUTENV='inherited')
        env.pop('JBCC_TEST_NEW_ENV', None)
        result = self.run_native(ROOT / 'tests/io/putenv.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('putenv.stdout'))

    def test_getenv(self):
        env = dict(os.environ, JBCC_TEST_VALUE='two words', JBCC_TEST_EMPTY='')
        env.pop('JBCC_TEST_ABSENT', None)
        result = self.run_native(ROOT / 'tests/io/getenv.b', env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('getenv.stdout'))

    def test_open_sections(self):
        run = self.run_native(ROOT / 'tests/io/open-sections.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-dict', 'CUSTOMERS',
                                       '--memory-file', 'DATA.ONLY', '--memory-dict', 'DICT.ONLY'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('open-sections.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_delete_records(self):
        run = self.run_native(ROOT / 'tests/io/delete.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('delete-records.stdout'))
        self.assertEqual(run.stderr, b'')

        source = ROOT / 'tests/io/delete-records.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('delete-records.stderr', source=source).encode(), run.stderr)

    def test_delete_locked_dispatch(self):
        source = ROOT / 'tests/io/delete-locked.b'
        run = self.run_native(source, options=['--memory-file', 'Records', '--memory-lock', 'Records', 'busy'])
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('delete-locked-dispatch.stdout'), b''))

    def test_file_lock_and_unlock(self):
        source = ROOT / 'tests/io/file-lock.b'
        options = ['--memory-file', 'Free', '--memory-file', 'Busy', '--memory-lock', 'Busy', 'held']
        run = self.run_native(source, options=options)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('file-lock-and-unlock.stdout'), b''))

    def test_clearfile(self):
        run = self.run_native(ROOT / 'tests/io/clearfile.b',
                              options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('clearfile.stdout'))
        self.assertEqual(run.stderr, b'')

        source = ROOT / 'tests/io/clearfile/clearfile.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('clearfile.stderr', source=source).encode(), run.stderr)

    def test_clearfile_locked_dispatch_preserves_records(self):
        source = ROOT / 'tests/io/clearfile-locked-dispatch-preserves-records.b'
        result = self.run_native(source, options=['--memory-file', 'Busy', '--memory-file', 'Free',
                                                  '--memory-lock', 'Busy', 'held'])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('clearfile-locked-dispatch-preserves-records.stdout'), b''))

    def test_read_setting_uses_record_status_and_branch_order(self):
        source = ROOT / 'tests/io/read-setting-uses-record-status-and-branch-order.b'
        result = self.run_native(source, options=['--memory-file', 'Sample'])
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('read-setting-uses-record-status-and-branch-order.stdout'), b''))

    def test_read_setting_requires_destination_and_conditional_arm(self):
        for fixture_name, diagnostic in (
            ('read-setting_1.b', expected_text('read-setting-requires-destination-and-conditional-arm.stderr')),
            ('read-setting_2.b', expected_text('read-setting-requires-destination-and-conditional-arm_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/read-setting-requires-destination-and-conditional-arm' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(f'{source}{diagnostic}', result.stderr)

    def test_readu(self):
        run = self.run_native(ROOT / 'tests/io/readu.b', ROOT / 'tests/io/reopen.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('readu.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_readu_unhandled_fixture_conflict(self):
        source = ROOT / 'tests/io/readu-unhandled-fixture-conflict.b'
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('readu-unhandled-fixture-conflict.stderr', source=source).encode(), run.stderr)

    def test_recordlocku_reserves_key_and_reports_contention(self):
        source = ROOT / 'tests/io/recordlocku-reserves-key-and-reports-contention.b'
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('recordlocku-reserves-key-and-reports-contention.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_recordlocku_unhandled_contention_reports_call_site(self):
        source = ROOT / 'tests/io/recordlocku-unhandled-contention-reports-call-site.b'
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('recordlocku-unhandled-contention-reports-call-site.stderr', source=source).encode(),
                      run.stderr)

    def test_release_on_error_reports_invalid_files_and_preserves_foreign_locks(self):
        source = ROOT / 'tests/io/release-on-error-reports-invalid-files-and-preserves-foreign-locks.b'
        result = self.run_native(source, options=(
            '--memory-file', 'F', '--memory-file', 'G', '--memory-lock', 'F', 'busy',
        ))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('release-on-error-reports-invalid-files-and-preserves-foreign-locks.stdout'), b''))

    def test_assign_system_resets_blocked_record_lock_counter(self):
        source = ROOT / 'tests/io/assign-system-resets-blocked-record-lock-counter.b'
        run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('assign-system-resets-blocked-record-lock-counter.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_assign_system_diagnostics(self):
        for fixture_name, diagnostic in (
            ('assign-system_1.b', expected_text('assign-system-diagnostics.stderr')),
            ('assign-system_2.b', expected_text('assign-system-diagnostics_2.stderr')),
            ('assign-system_3.b', expected_text('assign-system-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/assign-system-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('assign-system-diagnostics_4.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_readv(self):
        run = self.run_native(ROOT / 'tests/io/readv.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('readv.stdout'))
        self.assertEqual(run.stderr, b'')

        source = ROOT / 'tests/io/readv/readv.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('readv.stderr', source=source).encode(), run.stderr)

    def test_readvu(self):
        run = self.run_native(ROOT / 'tests/io/readvu.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('readvu.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_readvu_diagnostics(self):
        for fixture_name, diagnostic in (
            ('readvu_1.b', expected_text('readvu-diagnostics.stderr')),
            ('readvu_2.b', expected_text('readvu-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/readvu-diagnostics' / fixture_name
                run = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('readvu-diagnostics_3.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_write_setting_and_on_error(self):
        result = self.run_native(ROOT / 'tests/io/write-error.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('write-setting-and-on-error.stdout'))

    def test_write_on_error_diagnostics(self):
        source = ROOT / 'tests/io/write-on-error-diagnostics/write.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('write-on-error-diagnostics.stderr', source=source), result.stderr)
        source = ROOT / 'tests/io/write-on-error-diagnostics/write-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('write-on-error-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_writeu(self):
        result = self.run_native(ROOT / 'tests/io/writeu.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('writeu.stdout'))

    def test_writeu_unhandled_failure(self):
        source = ROOT / 'tests/io/writeu-unhandled-failure.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('writeu-unhandled-failure.stderr', source=source).encode(), result.stderr)

    def test_writev_and_writevu(self):
        result = self.run_native(ROOT / 'tests/io/writev.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('writev-and-writevu.stdout'))

    def test_writev_field_number_diagnostics(self):
        for fixture_name, op in (
            ('writev_1.b', 'WRITEV'),
            ('writev_2.b', 'WRITEVU'),
            ('writev_3.b', 'WRITEV'),
            ('writev_4.b', 'WRITEVU'),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/writev-field-number-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('writev-field-number-diagnostics.stderr', source=source, op=op).encode(),
                              result.stderr)

    def test_inmat_dimensions_and_latest_load(self):
        result = self.run_native(ROOT / 'tests/io/inmat.b', ROOT / 'tests/io/inmat-shape.b',
                                 options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('inmat-dimensions-and-latest-load.stdout'))

    def test_inmat_requires_a_matrix_argument(self):
        source = ROOT / 'tests/io/inmat-requires-a-matrix-argument.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('inmat-requires-a-matrix-argument.stderr', source=source), result.stderr)

    def test_matread(self):
        run = self.run_native(ROOT / 'tests/io/matread.b', options=['--memory-file', 'CUSTOMERS'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('matread.stdout'))
        self.assertEqual(run.stderr, b'')

        source = ROOT / 'tests/io/matread/matread.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matread.stderr', source=source), run.stderr)
        source = ROOT / 'tests/io/matread/matread-variant-2.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matread_2.stderr', source=source), run.stderr)

    def test_matreadu(self):
        run = self.run_native(ROOT / 'tests/io/matreadu.b',
                              options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('matreadu.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_matwrite(self):
        run = self.run_native(ROOT / 'tests/io/matwrite.b',
                              options=['--memory-file', 'EXPLICIT', '--memory-file', 'DEFAULT'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('matwrite.stdout'))
        self.assertEqual(run.stderr, b'')
        source = ROOT / 'tests/io/matwrite/matwrite.b'
        run = self.run_native(source, options=['--memory-file', 'F'])
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matwrite.stderr', source=source).encode(), run.stderr)

    def test_formlist_rejects_out_of_range_quoted_list_number(self):
        source = ROOT / 'tests/programs/formlist-invalid-number.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual((result.returncode, result.stderr),
                         (1, expected_text('formlist-rejects-out-of-range-quoted-list-number.stderr', source=source)))

    def test_file_select(self):
        run = self.run_native(ROOT / 'tests/io/select.b', options=['--memory-file', 'F'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('file-select.stdout'))
        self.assertEqual(run.stderr, b'')
        source = ROOT / 'tests/io/file-select.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('file-select.stderr', source=source), run.stderr)

    def test_sselect_file(self):
        result = self.run_native(ROOT / 'tests/io/sselect.b', options=['--memory-file', 'F'])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, b'')
        self.assertEqual(result.stdout, expected_bytes('sselect-file.stdout'))

    def test_sselect_diagnostics(self):
        source = ROOT / 'tests/io/sselect-diagnostics/sselect.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('sselect-diagnostics.stderr', source=source), result.stderr)
        source = ROOT / 'tests/io/sselect-diagnostics/sselect-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('sselect-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_clearselect(self):
        run = self.run_native(ROOT / 'tests/io/clearselect.b', options=['--memory-file', 'F'])
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('clearselect.stdout'))
        self.assertEqual(run.stderr, b'')
        source = ROOT / 'tests/io/clearselect/clearselect.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('clearselect.stderr', source=source), run.stderr)
        source = ROOT / 'tests/io/clearselect/clearselect-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('clearselect_2.stderr', source=source).encode(), run.stderr)

    def test_cursor_coordinate_diagnostics(self):
        for fixture_name, message in (
            ('cursor_1.b', expected_text('cursor-coordinate-diagnostics.stderr')),
            ('cursor_2.b', expected_text('cursor-coordinate-diagnostics_2.stderr')),
            ('cursor_3.b', expected_text('cursor-coordinate-diagnostics_2.stderr')),
            ('cursor_4.b', expected_text('cursor-coordinate-diagnostics_3.stderr')),
            ('cursor_5.b', expected_text('cursor-coordinate-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/cursor-coordinate-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('cursor-coordinate-diagnostics_4.stderr', source=source, message=message).encode(), run.stderr)

    def test_invocation_sentence(self):
        routine = ROOT / 'tests/routines/get.sentence.b'
        binary = self.work / 'invocation'
        for case_number, direct_read in enumerate((False, True), 1):
            source = ROOT / 'tests/routines/invocation-sentence' / f'caller_{case_number}.b'
            subprocess.run([CLI, '--exe', routine, source, '-o', binary], check=True)
            for variant, args in enumerate(([], ['42', 'two words', '', 'last']), 1):
                with self.subTest(direct_read=direct_read, args=args):
                    run = subprocess.run(['./invocation', *args], cwd=self.work, capture_output=True)
                    self.assertEqual(run.returncode, 0, run.stderr)
                    expected = expected_bytes(f'invocation-sentence_{case_number}_{variant}.stdout')
                    self.assertEqual(run.stdout, expected)

    def test_command_system_variable_uses_the_invocation_in_a_subroutine(self):
        binary = self.work / 'invocation'
        source = ROOT / 'tests/routines/command-system-variable-uses-the-invocation-in-a-subroutine/caller.b'
        routine = ROOT / 'tests/routines/command-system-variable-uses-the-invocation-in-a-subroutine/command.b'
        subprocess.run([CLI, '--exe', routine, source, '-o', binary], check=True)
        for variant, args in enumerate(([], ['first', 'two words', '', 'last']), 1):
            with self.subTest(args=args):
                run = subprocess.run(['./invocation', *args], cwd=self.work, capture_output=True, timeout=5)
                expected = expected_bytes(f'command-system-variable-uses-the-invocation-in-a-subroutine_{variant}.stdout')
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected, b''))

    def test_sentence_function_reads_invocation_in_a_subroutine(self):
        binary = self.work / 'invocation'
        source = ROOT / 'tests/routines/sentence-function-reads-invocation-in-a-subroutine/caller.b'
        routine = ROOT / 'tests/routines/sentence-function-reads-invocation-in-a-subroutine/show.b'
        subprocess.run([CLI, '--exe', source, routine, '-o', binary], check=True)
        for variant, args in enumerate(([], ['first', 'two words', '', 'last']), 1):
            with self.subTest(args=args):
                expected = expected_bytes(f'sentence-function-reads-invocation-in-a-subroutine_{variant}.stdout')
                run = subprocess.run(['./invocation', *args], cwd=self.work, capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected, b''))

    def test_parasentence_uses_launch_context_or_invocation(self):
        sources = ROOT / 'tests/routines'
        binary = self.work / 'invocation'
        subprocess.run([CLI, '--exe', sources / 'parasentence-main.b',
                        sources / 'show-parasentence.b', '-o', binary], check=True)
        for supplied in (None, '', 'NIGHTLY  REPORT'):
            with self.subTest(supplied=supplied):
                env = dict(os.environ)
                env.pop('JBCC_PARASENTENCE', None)
                if supplied is not None:
                    env['JBCC_PARASENTENCE'] = supplied
                invocation = './invocation two words'
                expected = expected_text('parasentence-uses-launch-context-or-invocation.stdout', value_1=supplied or invocation, invocation=invocation).encode() * 2
                run = subprocess.run(['./invocation', 'two words'], cwd=self.work, env=env,
                                     capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected, b''))

    def test_sentence_function_preserves_get_argument_cursor(self):
        binary = self.work / 'args'
        source = ROOT / 'tests/routines/sentence-function-preserves-get-argument-cursor.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        run = subprocess.run([binary, 'one', 'two', 'three'], capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected_bytes('sentence-function-preserves-get-argument-cursor.stdout'), b''))

    def test_sentence_function_diagnostics(self):
        source = ROOT / 'tests/routines/sentence-function-diagnostics/sentence.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('sentence-function-diagnostics.stderr', source=source).encode(), result.stderr)
        for fixture_name in (
            'sentence-variant-2_1.b',
            'sentence-variant-2_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/sentence-function-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('sentence-function-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_get_argument_preserves_argv_and_shares_cursor_across_routines(self):
        binary = self.work / 'args'
        source = ROOT / 'tests/routines/get-argument-preserves-argv-and-shares-cursor-across-routines/args.b'
        routine = ROOT / 'tests/routines/get-argument-preserves-argv-and-shares-cursor-across-routines/next.b'
        subprocess.run([CLI, '--exe', source, routine, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        result = subprocess.run([binary, 'first', 'two words', '', 'last'],
                                capture_output=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('get-argument-preserves-argv-and-shares-cursor-across-routines.stdout'), b''))

    def test_get_argument_failures_and_diagnostics(self):
        source = ROOT / 'tests/routines/get-argument-failures-and-diagnostics/args.b'
        result = self.run_native(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('get-argument-failures-and-diagnostics.stdout'), b''))
        source = ROOT / 'tests/routines/get-argument-failures-and-diagnostics/args-variant-2.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('get-argument-failures-and-diagnostics.stderr', source=source).encode(), result.stderr)
        source = ROOT / 'tests/routines/get-argument-failures-and-diagnostics/args-variant-3.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('get-argument-failures-and-diagnostics_2.stderr', source=source), result.stderr)

    def test_input_from_pipe(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input.b', '-o', binary], check=True)
        first = b'  ' + b'x' * 512 + b'  '
        run = subprocess.run([binary], input=first + b'\n\nlast', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('input-from-pipe.stdout'))
        run = subprocess.run([binary], input=b'a\0b\n', capture_output=True, timeout=5)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_bytes('input-from-pipe.stderr'), run.stderr)

    def test_positioned_input_writes_cursor_before_prompt(self):
        source = ROOT / 'tests/io/input-positioned.b'
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        run = subprocess.run([binary], input=b'first\nsecond\n', capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('positioned-input-writes-cursor-before-prompt.stdout'), b''))

    def test_length_limited_input_from_pipe(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input-limit.b', '-o', binary], check=True)
        run = subprocess.run([binary], input=b'abcde\nx\nend', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('length-limited-input-from-pipe.stdout'))

    def test_inputclear_discards_only_terminal_typeahead(self):
        binary = self.work / 'input'

        def read_until(fd, marker):
            data = bytearray()
            while not data.endswith(marker):
                self.assertTrue(select.select([fd], [], [], 5)[0], data)
                data.extend(os.read(fd, 1024))
            return bytes(data)

        for fixture_name in (
            'input_1.b',
            'input_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/inputclear-discards-only-terminal-typeahead' / fixture_name
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
                run = subprocess.run([binary], input=b'pipe\n', capture_output=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected_bytes('inputclear-discards-only-terminal-typeahead.stdout'))
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
                        self.assertEqual(read_until(master, b'>'), expected_bytes('inputclear-discards-only-terminal-typeahead_2.stdout'))
                        os.write(master, b'fresh\n')
                        self.assertEqual(read_until(master, b'\r\n'), expected_bytes('inputclear-discards-only-terminal-typeahead_3.stdout'))
                        self.assertEqual(proc.wait(timeout=5), 0)
                    finally:
                        if proc.poll() is None:
                            proc.kill()

    def test_input_underscore_discards_excess_in_queue_and_pipe(self):
        source = ROOT / 'tests/io/input-underscore-discards-excess-in-queue-and-pipe.b'
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        run = subprocess.run([binary], input=b'first\nsecond\nlast', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('input-underscore-discards-excess-in-queue-and-pipe.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_input_underscore_rings_bell_and_waits_for_enter(self):
        source = ROOT / 'tests/io/input-underscore-rings-bell-and-waits-for-enter.b'
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
                self.assertEqual(read_until(b'>'), expected_bytes('input-underscore-rings-bell-and-waits-for-enter.stdout'))
                os.write(master, b'ab')
                self.assertEqual(read_until(b'\a'), expected_bytes('input-underscore-rings-bell-and-waits-for-enter_2.stdout'))
                os.write(master, b'\n')
                self.assertEqual(read_until(b'\r\n'), expected_bytes('input-underscore-rings-bell-and-waits-for-enter_3.stdout'))
                self.assertEqual(proc.wait(timeout=5), 0)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_plain_execute_and_perform(self):
        run = self.run_native(ROOT / 'tests/programs/execute.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('plain-execute-and-perform.stdout'))
        self.assertEqual(run.stderr, expected_bytes('plain-execute-and-perform.stderr'))

    def test_capturing(self):
        run = self.run_native(ROOT / 'tests/programs/capturing.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('capturing.stdout'))
        self.assertEqual(run.stderr, expected_bytes('capturing.stderr'))

    def test_capture_from_pipe(self):
        source = ROOT / 'tests/programs/capture-from-pipe.b'
        binary = self.work / 'capture'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        payload = b'x' * (256 * 1024) + b'\r\n\xff'
        run = subprocess.run([binary], input=payload, capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, payload.replace(b'\n', b'\xfe'))
        run = subprocess.run([binary], input=b'one\x00two', capture_output=True, timeout=5)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('capture-from-pipe.stderr', source=source).encode(), run.stderr)

    def test_exec_rejects_duplicate_returning_clause(self):
        source = ROOT / 'tests/programs/exec-rejects-duplicate-returning-clause.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('exec-rejects-duplicate-returning-clause.stderr', source=source), result.stderr)

    def test_execute_large_stdout_and_stderr(self):
        source = ROOT / 'tests/programs/execute-large-stdout-and-stderr.b'
        binary = self.work / 'execute'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        payload = b'x' * (256 * 1024)
        run = subprocess.run([binary], input=payload, timeout=5, capture_output=True)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('execute-large-stdout-and-stderr.stdout') + b'1\xfe' * 65536 + b'\n' + payload)
        self.assertEqual(run.stderr, b'')

    def test_execute_result_diagnostics(self):
        for fixture_name, repeated in (
            ('execute_1.b', 'RETURNING'),
            ('execute_2.b', 'CAPTURING'),
            ('execute_3.b', 'RTNLIST'),
        ):
            source = ROOT / 'tests/programs/execute-result-diagnostics' / fixture_name
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
            column = source.read_text().rindex(repeated) + 1
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('execute-result-diagnostics.stderr', source=source, column=column, repeated=repeated).encode(), run.stderr)
        source = ROOT / 'tests/programs/execute-result-diagnostics/execute-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('execute-result-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_execute_rtnlist_requires_backend_before_running_command(self):
        marker = self.work / 'child-ran'
        for fixture_name in (
            'select_1.b',
            'select_2.b',
            'select_3.b',
            'select_4.b',
            'select_5.b',
            'select_6.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/execute-rtnlist-requires-backend-before-running-command' / fixture_name
                run = self.run_native(source, cwd=self.work)
                self.assertEqual(run.returncode, 1, run.stderr)
                self.assertEqual(run.stdout, expected_bytes('execute-rtnlist-requires-backend-before-running-command.stdout'))
                self.assertEqual(
                    run.stderr, expected_text('execute-rtnlist-requires-backend-before-running-command.stderr', source=source).encode()
                )
                self.assertFalse(marker.exists())

    def test_execute_child_program(self):
        child = ROOT / 'tests/programs/execute-child-program/child.b'
        subprocess.run([CLI, '--exe', child, '-o', self.work / 'child'], check=True)
        main = ROOT / 'tests/programs/execute-child-program/main.b'
        sub = ROOT / 'tests/programs/execute-child-program/sub.b'
        binary = self.work / 'main'
        subprocess.run([CLI, '--exe', main, sub, '-o', binary], check=True)
        run = subprocess.run([binary], cwd=self.work, input=b'hello\n', capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('execute-child-program.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_execute_command_diagnostics(self):
        for fixture_name, message in (
            ('command_1.b', expected_text('execute-command-diagnostics.stderr')),
            ('command_2.b', expected_text('execute-command-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/execute-command-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('execute-command-diagnostics_3.stderr', source=source, message=message).encode(), run.stderr)

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
                self.assertEqual(run.stdout, expected_bytes('sleep-duration-and-default.stdout'))
        for value, message in [('-0.1', expected_text('sleep-duration-and-default_2.stderr')), ('later', expected_text('sleep-duration-and-default_2.stderr')),
                               ('08:30', expected_text('sleep-duration-and-default_3.stderr'))]:
            with self.subTest(value=value):
                run = subprocess.run(['pause', value], executable=binary, capture_output=True, timeout=5)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('sleep-duration-and-default.stderr', source=source).encode(), run.stderr)
                self.assertIn(message.encode(), run.stderr)

    def test_keyin_shares_queued_and_piped_input(self):
        binary = self.work / 'keyin'
        source = ROOT / 'tests/io/keyin-shares-queued-and-piped-input.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'xyz\n', capture_output=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('keyin-shares-queued-and-piped-input.stdout'), b''))

    def test_keyin_reads_unedited_terminal_byte_and_restores_mode(self):
        binary = self.work / 'keyin'
        source = ROOT / 'tests/io/keyin-reads-unedited-terminal-byte-and-restores-mode.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)
        original[3] |= termios.ICANON | termios.ECHO | termios.ISIG
        original[6][termios.VERASE] = b'\x7f'
        termios.tcsetattr(slave, termios.TCSANOW, original)

        for value in (b'\x7f', b'\x00', None):
            with self.subTest(value=value), subprocess.Popen(
                    [binary], stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
                try:
                    self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                    self.assertEqual(proc.stdout.readline(), expected_bytes('keyin-reads-unedited-terminal-byte-and-restores-mode.stdout'))
                    deadline = time.monotonic() + 5
                    while (mode := termios.tcgetattr(slave))[3] & termios.ICANON:
                        self.assertLess(time.monotonic(), deadline, 'KEYIN did not enter noncanonical mode')
                        time.sleep(0.01)
                    self.assertFalse(mode[3] & termios.ECHO)
                    self.assertTrue(mode[3] & termios.ISIG)
                    if value is None:
                        proc.terminate()
                    else:
                        os.write(master, value)
                    stdout, stderr = proc.communicate(timeout=5)
                    expected = {
                        b'\x7f': (0, b'127\n', b''),
                        b'\x00': (1, b'', f'{source}:2:9: KEYIN cannot store a NUL byte\n'.encode()),
                        None: (-signal.SIGTERM, b'', b''),
                    }
                    self.assertEqual((proc.returncode, stdout, stderr), expected[value])
                    actual = termios.tcgetattr(slave)
                    actual[3] &= ~getattr(termios, 'PENDIN', 0)
                    self.assertEqual(actual, original)
                finally:
                    if proc.poll() is None:
                        proc.kill()

    def test_keyin_function_diagnostics(self):
        for case_number, function in enumerate(('KEYIN', 'IN'), 1):
            with self.subTest(function=function):
                source = ROOT / 'tests/io/keyin-function-diagnostics' / f'keyin_{case_number}.b'
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('keyin-function-diagnostics.stderr', source=source, function=function).encode(),
                              result.stderr)

    def test_timed_input_restarts_after_each_byte(self):
        binary = self.work / 'input'
        subprocess.run([CLI, '--exe', ROOT / 'tests/io/input-timeout.b', '-o', binary], check=True)
        for data in (b'x\n', b'x'):
            run = subprocess.run([binary], input=data, capture_output=True, timeout=5)
            self.assertEqual(run.returncode, 0, run.stderr)
            self.assertEqual(run.stdout, expected_bytes('timed-input-restarts-after-each-byte.stdout'))
        with subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.read(1), expected_bytes('timed-input-restarts-after-each-byte_2.stdout'))
                for byte in (b'a', b'b', b'c'):
                    proc.stdin.write(byte)
                    proc.stdin.flush()
                    if byte != b'c':
                        time.sleep(0.6)
                self.assertEqual(proc.wait(timeout=5), 0)
                self.assertEqual(proc.stdout.read(), expected_bytes('timed-input-restarts-after-each-byte_3.stdout'))
            finally:
                proc.kill()

    def test_timed_input_diagnostics(self):
        source = ROOT / 'tests/io/timed-input-diagnostics/input.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('timed-input-diagnostics.stderr', source=source).encode(), run.stderr)
        source = ROOT / 'tests/io/timed-input-diagnostics/input-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('timed-input-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_input_negative_one_polls_without_consuming_bytes(self):
        binary = self.work / 'input-poll'
        source = ROOT / 'tests/io/input-negative-one-polls-without-consuming-bytes.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        read_fd, write_fd = os.pipe()
        with os.fdopen(write_fd, 'wb') as writer:
            writer.write(b'z')
        with os.fdopen(read_fd, 'rb') as reader:
            run = subprocess.run([binary], stdin=reader, capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('input-negative-one-polls-without-consuming-bytes.stdout'), b''))

    def test_input_negative_one_polls_an_empty_open_pipe(self):
        binary = self.work / 'input-poll'
        source = ROOT / 'tests/io/input-negative-one-polls-an-empty-open-pipe.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        with subprocess.Popen([binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as proc:
            try:
                self.assertEqual(proc.wait(timeout=5), 0)
                self.assertEqual((proc.stdout.read(), proc.stderr.read()), (expected_bytes('input-negative-one-polls-an-empty-open-pipe.stdout'), b''))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_input_negative_one_detects_terminal_typeahead(self):
        binary = self.work / 'input-poll'
        source = ROOT / 'tests/io/input-negative-one-detects-terminal-typeahead.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        original = termios.tcgetattr(slave)
        original[3] |= termios.ICANON
        termios.tcsetattr(slave, termios.TCSANOW, original)
        with subprocess.Popen([binary], stdin=slave, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as proc:
            try:
                self.assertTrue(select.select([proc.stdout], [], [], 5)[0])
                self.assertEqual(proc.stdout.readline(), expected_bytes('input-negative-one-detects-terminal-typeahead.stdout'))
                os.write(master, b'q')
                stdout, stderr = proc.communicate(timeout=5)
                self.assertEqual((proc.returncode, stdout, stderr), (0, expected_bytes('input-negative-one-detects-terminal-typeahead_2.stdout'), b''))
                actual = termios.tcgetattr(slave)
                actual[3] &= ~getattr(termios, 'PENDIN', 0)
                self.assertEqual(actual, original)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_input_length_diagnostics(self):
        for fixture_name, message in (
            ('input_1.b', expected_text('input-length-diagnostics.stderr')),
            ('input_2.b', expected_text('input-length-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/io/input-length-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('input-length-diagnostics_3.stderr', source=source, message=message).encode(), run.stderr)

    def test_hush_nonnumeric_operand(self):
        source = ROOT / 'tests/io/hush-nonnumeric-operand.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('hush-nonnumeric-operand.stderr', source=source).encode(), result.stderr)

    def test_break_key_controls_terminal_interrupts(self):
        source = ROOT / 'tests/io/break-key-controls-terminal-interrupts.b'
        binary = self.work / 'break-key'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        mode = termios.tcgetattr(slave)
        mode[3] |= termios.ICANON | termios.ISIG
        mode[6][termios.VINTR] = b'\x03'
        termios.tcsetattr(slave, termios.TCSANOW, mode)

        # Attach the slave as the child's controlling terminal so VINTR sends SIGINT.
        launch = ('import fcntl, os, sys, termios\n'
                  'fcntl.ioctl(0, termios.TIOCSCTTY, 0)\n'
                  'os.execv(sys.argv[1], sys.argv[1:])')
        with subprocess.Popen([sys.executable, '-c', launch, str(binary)], stdin=slave,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              start_new_session=True) as proc:
            def expect_output(expected):
                received = bytearray()
                while len(received) < len(expected):
                    self.assertTrue(select.select([proc.stdout], [], [], 5)[0], received)
                    chunk = os.read(proc.stdout.fileno(), len(expected) - len(received))
                    self.assertTrue(chunk, received)
                    received.extend(chunk)
                self.assertEqual(received, expected)

            try:
                expect_output(expected_bytes('break-key-controls-terminal-interrupts.stdout'))
                os.write(master, b'\x03ok\n')
                expect_output(expected_bytes('break-key-controls-terminal-interrupts_2.stdout'))
                os.write(master, b'\x03')
                self.assertEqual(proc.wait(timeout=5), -signal.SIGINT)
                self.assertEqual(proc.stderr.read(), b'')
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_echo_controls_terminal_input_and_system24(self):
        source = ROOT / 'tests/io/echo-controls-terminal-input-and-system24.b'
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
                self.assertEqual(read_until(b'>'), expected_bytes('echo-controls-terminal-input-and-system24.stdout'))
                os.write(master, b'secret\n')
                self.assertEqual(read_until(b'>'), expected_bytes('echo-controls-terminal-input-and-system24_2.stdout'))
                os.write(master, b'visible\n')
                self.assertEqual(read_until(b'1\r\n0\r\n'), expected_bytes('echo-controls-terminal-input-and-system24_3.stdout'))
                self.assertEqual(proc.wait(timeout=5), 0)
                actual = termios.tcgetattr(slave)
                actual[3] &= ~getattr(termios, 'PENDIN', 0)
                self.assertEqual(actual, original)
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_hush_terminal_input_and_printer(self):
        source = ROOT / 'tests/io/hush-terminal-input-and-printer.b'
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
                self.assertEqual(output, expected_bytes('hush-terminal-input-and-printer.stdout'))
                self.assertTrue(termios.tcgetattr(slave)[3] & termios.ECHO)
                os.write(master, b'ok\n')
                self.assertEqual(proc.wait(timeout=5), 0)
            finally:
                proc.kill()
        self.assertEqual([p.read_bytes() for p in self.work.glob('unit-1-*')], [b'job\n'])

    def test_input_terminal_echo(self):
        source = ROOT / 'tests/io/input-terminal-echo.b'
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
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo.stdout'))
                os.write(master, b'ax')
                self.assertEqual(read_until(b'x'), expected_bytes('input-terminal-echo_2.stdout'))
                os.write(master, original[6][termios.VERASE] + b'b\n')
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo_3.stdout'))
                os.write(master, b'c\n')
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo_4.stdout'))
                os.write(master, b'xy')
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo_5.stdout'))
                os.write(master, b'z')
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo_6.stdout'))
                os.write(master, b'ab')
                self.assertEqual(proc.wait(timeout=5), 0)
                self.assertEqual(read_until(b'""\r\n'), expected_bytes('input-terminal-echo_7.stdout'))
                check_mode_restored()
            finally:
                proc.kill()

        with subprocess.Popen([binary], stdin=slave, stdout=slave, stderr=slave) as proc:
            try:
                self.assertEqual(read_until(b'?'), expected_bytes('input-terminal-echo.stdout'))
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
        blank = expected_bytes('banner.stdout')
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
        source = ROOT / 'tests/io/system14-input-queue.b'
        binary = self.work / 'pending'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        with open(os.devnull, 'rb') as empty:
            result = subprocess.run([binary], stdin=empty, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('system14-input-queue.stdout'), b''))
        # Preload the pipe before starting the program. Polling leaves its bytes queued.
        read_fd, write_fd = os.pipe()
        with os.fdopen(write_fd, 'wb') as writer:
            writer.write(b'abc')
        with os.fdopen(read_fd, 'rb') as reader:
            result = subprocess.run([binary], stdin=reader, capture_output=True, timeout=5)
            self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('system14-input-queue_2.stdout'), b''))

    def test_account_path_uses_working_directory(self):
        source = ROOT / 'tests/programs/account-path-uses-working-directory.b'
        cwd = self.work.joinpath(*(['directory-' + 'x' * 60] * 4))
        cwd.mkdir(parents=True)
        env = dict(os.environ, HOME='/unused-home', PWD='/unused-pwd')
        result = self.run_native(source, env=env, cwd=cwd)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, os.fsencode(cwd.resolve()) + b'\n')
        self.assertEqual(result.stderr, b'')

    def test_terminal_type_aliases_follow_term(self):
        source = ROOT / 'tests/programs/terminal-type-aliases-follow-term.b'
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
                self.assertEqual(result.stdout, expected_text('terminal-type-aliases-follow-term.stdout', value_1=name).encode())
                self.assertEqual(result.stderr, b'')

    def test_tty_name_with_terminal_and_redirected_input(self):
        source = ROOT / 'tests/programs/tty-name-with-terminal-and-redirected-input.b'
        binary = self.work / 'tty'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)

        master, slave = os.openpty()
        self.addCleanup(os.close, master)
        self.addCleanup(os.close, slave)
        terminal = os.fsencode(os.ttyname(slave))
        for stdin, expected in ((slave, terminal), (subprocess.DEVNULL, expected_bytes('tty-name-with-terminal-and-redirected-input_2.stdout'))):
            with self.subTest(stdin=stdin):
                run = subprocess.run([binary], stdin=stdin, capture_output=True, timeout=5)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected_bytes('tty-name-with-terminal-and-redirected-input.stdout') + expected + expected_bytes('tty-name-with-terminal-and-redirected-input_3.stdout') + expected[:1] + b'\n')
                self.assertEqual(run.stderr, b'')

    def test_port_number_aliases_use_startup_environment(self):
        main = ROOT / 'tests/programs/port-number-aliases-use-startup-environment/main.b'
        routine = ROOT / 'tests/programs/port-number-aliases-use-startup-environment/show.port.b'
        for variant, setting in enumerate(('00042', '0'), 1):
            with self.subTest(setting=setting):
                run = self.run_native(main, routine, env=dict(os.environ, JBCPORTNO=setting))
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected_bytes(f'port-number-aliases-use-startup-environment_{variant}.stdout'))
                self.assertEqual(run.stderr, b'')

    def test_pid_uses_native_process_id_with_port_override(self):
        source = ROOT / 'tests/programs/pid-uses-native-process-id-with-port-override.b'
        binary = self.work / 'pid'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        with subprocess.Popen([binary], env=dict(os.environ, JBCPORTNO='0'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual(proc.returncode, 0, stderr)
            self.assertEqual(stdout, expected_text('pid-uses-native-process-id-with-port-override.stdout', value_1=proc.pid).encode())
            self.assertEqual(stderr, b'')

    def test_user_root_is_shared_with_linked_routines_and_userstats(self):
        source = ROOT / 'tests/programs/user-root-is-shared-with-linked-routines-and-userstats/main.b'
        routine = ROOT / 'tests/programs/user-root-is-shared-with-linked-routines-and-userstats/publish.b'
        run = self.run_native(source, routine, env=dict(os.environ, JBCPORTNO='1'))
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('user-root-is-shared-with-linked-routines-and-userstats.stdout'), b''))

    def test_user_root_limit_counts_bytes(self):
        source = ROOT / 'tests/programs/user-root-limit-counts-bytes.b'
        run = self.run_native(source)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (1, b'', expected_text('user-root-limit-counts-bytes.stderr', source=source).encode()))

    def test_userstats_native_snapshot_and_record_writes(self):
        binary = self.work / 'stats'
        source = ROOT / 'tests/programs/userstats-native-snapshot-and-record-writes/main.b'
        routine = ROOT / 'tests/programs/userstats-native-snapshot-and-record-writes/stats.b'
        env = dict(os.environ, JBCPORTNO='93', JBCLOGNAME='stats-user', TERM='stats-terminal')
        subprocess.run([CLI, '--exe', '--memory-file', 'F', '--memory-lock', 'F', 'held',
                        source, routine, '-o', binary], check=True,
                       env=dict(env, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        start = int(time.time())
        with subprocess.Popen([binary, 'two words'], env=env, stdin=subprocess.DEVNULL,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE) as proc:
            stdout, stderr = proc.communicate(timeout=5)
            self.assertEqual((proc.returncode, stderr), (0, b''))
            lines = stdout.splitlines()
            self.assertEqual(lines[:2], [expected_bytes('userstats-native-snapshot-and-record-writes.stdout'), expected_text('userstats-native-snapshot-and-record-writes_2.stdout', value_1=proc.pid).encode()])
            self.assertLessEqual(start, int(lines[2]))
            self.assertLessEqual(int(lines[2]), int(time.time()))
            self.assertEqual(lines[3:], [
                expected_bytes('userstats-native-snapshot-and-record-writes_3.stdout'), expected_bytes('userstats-native-snapshot-and-record-writes_4.stdout'),
                expected_text('userstats-native-snapshot-and-record-writes_5.stdout', binary=binary).encode(), expected_bytes('userstats-native-snapshot-and-record-writes_6.stdout'), str(routine).encode()])

    def test_userstats_open_and_read_counters(self):
        source = ROOT / 'tests/programs/userstats-open-and-read-counters.b'
        result = self.run_native(source, options=['--memory-file', 'F', '--memory-lock', 'F', 'held'],
                                 env=dict(os.environ, JBCPORTNO='1'))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('userstats-open-and-read-counters.stdout'), b''))

    def test_userstats_delete_and_clearfile_counters(self):
        source = ROOT / 'tests/programs/userstats-delete-and-clearfile-counters.b'
        result = self.run_native(source, options=['--memory-file', 'F', '--memory-file', 'Busy',
                                                  '--memory-lock', 'Busy', 'held'],
                                 env=dict(os.environ, JBCPORTNO='1'))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('userstats-delete-and-clearfile-counters.stdout'), b''))

    def test_userstats_execute_and_input_counters(self):
        binary = self.work / 'terminal-stats'
        source = ROOT / 'tests/programs/userstats-execute-and-input-counters.b'
        env = dict(os.environ, JBCPORTNO='1')
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(env, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        with subprocess.Popen([binary], env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE) as proc:
            try:
                expected = expected_bytes('userstats-execute-and-input-counters.stdout')
                received = bytearray()
                while len(received) < len(expected):
                    self.assertTrue(select.select([proc.stdout], [], [], 5)[0], received)
                    chunk = os.read(proc.stdout.fileno(), len(expected) - len(received))
                    self.assertTrue(chunk, received)
                    received.extend(chunk)
                self.assertEqual(received, expected)
                proc.stdin.close()
                proc.stdin = None
                output, errors = proc.communicate(timeout=5)
                self.assertEqual((proc.returncode, output, errors), (0, expected_bytes('userstats-execute-and-input-counters_2.stdout'), b''))
            finally:
                if proc.poll() is None:
                    proc.kill()

    def test_userstats_reports_invalid_port_at_reference(self):
        source = ROOT / 'tests/programs/userstats-reports-invalid-port-at-reference.b'
        result = self.run_native(source, env=dict(os.environ, JBCPORTNO='bad'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('userstats-reports-invalid-port-at-reference.stderr', source=source).encode(), result.stderr)

    def test_port_number_defaults_to_process_id(self):
        source = ROOT / 'tests/programs/port-number-defaults-to-process-id.b'
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
        source = ROOT / 'tests/programs/invalid-port-number-reports-call-site.b'
        for setting in ('12-15', '42,43', '-1', '12.25', '9' * 80):
            with self.subTest(setting=setting):
                run = self.run_native(source, env=dict(os.environ, JBCPORTNO=setting))
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, expected_bytes('invalid-port-number-reports-call-site.stdout'))
                self.assertIn(
                    expected_text('invalid-port-number-reports-call-site.stderr', source=source).encode(),
                    run.stderr)

    def test_who_uses_startup_login_name(self):
        main = ROOT / 'tests/programs/who-uses-startup-login-name/main.b'
        routine = ROOT / 'tests/programs/who-uses-startup-login-name/show.login.b'
        for name, legacy, expected in [('MainAccount', 'Fallback', expected_text('who-uses-startup-login-name.stdout')),
                                       ('', 'GuideAccount', expected_text('who-uses-startup-login-name_2.stdout'))]:
            with self.subTest(name=name):
                env = dict(os.environ, JBCLOGNAME=name, JBASICLOGNAME=legacy)
                run = self.run_native(main, routine, env=env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected_text('who-uses-startup-login-name_3.stdout', expected=expected).encode())
                self.assertEqual(run.stderr, b'')

    def test_who_defaults_to_posix_user_name(self):
        source = ROOT / 'tests/programs/who-defaults-to-posix-user-name.b'
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
        main = ROOT / 'tests/programs/account-aliases-use-startup-account-name/main.b'
        routine = ROOT / 'tests/programs/account-aliases-use-startup-account-name/show.account.b'
        for override, unix_name, account, login in [
                ('Pseudo', 'Unix', 'Pseudo', 'Pseudo'),
                ('', 'Unix', 'Unix', 'GuideLogin'),
                ('', '', 'GuideLogin', 'GuideLogin')]:
            with self.subTest(override=override, unix_name=unix_name):
                env = dict(os.environ, JBCLOGNAME=override, LOGNAME=unix_name,
                           JBASICLOGNAME='GuideLogin')
                run = self.run_native(main, routine, env=env)
                self.assertEqual(run.returncode, 0, run.stderr)
                self.assertEqual(run.stdout, expected_text('account-aliases-use-startup-account-name.stdout', account=account, login=login).encode())
                self.assertEqual(run.stderr, b'')

    def test_account_defaults_to_posix_user_name(self):
        source = ROOT / 'tests/programs/account-defaults-to-posix-user-name.b'
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
