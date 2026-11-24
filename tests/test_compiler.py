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

    def test_diagnostics_preserve_existing_output(self):
        for fixture_name, location in (
            ('invalid_1.b', expected_text('diagnostics-preserve-existing-output.stderr')),
            ('invalid_2.b', expected_text('diagnostics-preserve-existing-output_2.stderr')),
            ('invalid_3.b', expected_text('diagnostics-preserve-existing-output_3.stderr')),
            ('invalid_4.b', expected_text('diagnostics-preserve-existing-output_2.stderr')),
            ('invalid_5.b', expected_text('diagnostics-preserve-existing-output_4.stderr')),
            ('invalid_6.b', expected_text('diagnostics-preserve-existing-output_5.stderr')),
            ('invalid_7.b', expected_text('diagnostics-preserve-existing-output_6.stderr')),
            ('invalid_8.b', expected_text('diagnostics-preserve-existing-output_7.stderr')),
            ('invalid_9.b', expected_text('diagnostics-preserve-existing-output_8.stderr')),
            ('invalid_10.b', expected_text('diagnostics-preserve-existing-output_9.stderr')),
            ('invalid_11.b', expected_text('diagnostics-preserve-existing-output_10.stderr')),
            ('invalid_12.b', expected_text('diagnostics-preserve-existing-output_11.stderr')),
            ('invalid_13.b', expected_text('diagnostics-preserve-existing-output_12.stderr')),
            ('invalid_14.b', expected_text('diagnostics-preserve-existing-output_13.stderr')),
            ('invalid_15.b', expected_text('diagnostics-preserve-existing-output_14.stderr')),
            ('invalid_16.b', expected_text('diagnostics-preserve-existing-output_15.stderr')),
            ('invalid_17.b', expected_text('diagnostics-preserve-existing-output_16.stderr')),
            ('invalid_18.b', expected_text('diagnostics-preserve-existing-output_17.stderr')),
            ('invalid_19.b', expected_text('diagnostics-preserve-existing-output_18.stderr')),
            ('invalid_20.b', expected_text('diagnostics-preserve-existing-output_19.stderr')),
            ('invalid_21.b', expected_text('diagnostics-preserve-existing-output_20.stderr')),
            ('invalid_22.b', expected_text('diagnostics-preserve-existing-output_21.stderr')),
            ('invalid_23.b', expected_text('diagnostics-preserve-existing-output_22.stderr')),
            ('invalid_24.b', expected_text('diagnostics-preserve-existing-output_22.stderr')),
            ('invalid_25.b', expected_text('diagnostics-preserve-existing-output_23.stderr')),
            ('invalid_26.b', expected_text('diagnostics-preserve-existing-output_24.stderr')),
            ('invalid_27.b', expected_text('diagnostics-preserve-existing-output_19.stderr')),
            ('invalid_28.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
            ('invalid_29.b', expected_text('diagnostics-preserve-existing-output_26.stderr')),
            ('invalid_30.b', expected_text('diagnostics-preserve-existing-output_27.stderr')),
            ('invalid_31.b', expected_text('diagnostics-preserve-existing-output_28.stderr')),
            ('invalid_32.b', expected_text('diagnostics-preserve-existing-output_29.stderr')),
            ('invalid_33.b', expected_text('diagnostics-preserve-existing-output_30.stderr')),
            ('invalid_34.b', expected_text('diagnostics-preserve-existing-output_31.stderr')),
            ('invalid_35.b', expected_text('diagnostics-preserve-existing-output_32.stderr')),
            ('invalid_36.b', expected_text('diagnostics-preserve-existing-output_33.stderr')),
            ('invalid_37.b', expected_text('diagnostics-preserve-existing-output_34.stderr')),
            ('invalid_38.b', expected_text('diagnostics-preserve-existing-output_35.stderr')),
            ('invalid_39.b', expected_text('diagnostics-preserve-existing-output_36.stderr')),
            ('invalid_40.b', expected_text('diagnostics-preserve-existing-output_37.stderr')),
            ('invalid_41.b', expected_text('diagnostics-preserve-existing-output_38.stderr')),
            ('invalid_42.b', expected_text('diagnostics-preserve-existing-output_38.stderr')),
            ('invalid_43.b', expected_text('diagnostics-preserve-existing-output_39.stderr')),
            ('invalid_44.b', expected_text('diagnostics-preserve-existing-output_40.stderr')),
            ('invalid_45.b', expected_text('diagnostics-preserve-existing-output_41.stderr')),
            ('invalid_46.b', expected_text('diagnostics-preserve-existing-output_42.stderr')),
            ('invalid_47.b', expected_text('diagnostics-preserve-existing-output_43.stderr')),
            ('invalid_48.b', expected_text('diagnostics-preserve-existing-output_44.stderr')),
            ('invalid_49.b', expected_text('diagnostics-preserve-existing-output_44.stderr')),
            ('invalid_50.b', expected_text('diagnostics-preserve-existing-output_45.stderr')),
            ('invalid_51.b', expected_text('diagnostics-preserve-existing-output_46.stderr')),
            ('invalid_52.b', expected_text('diagnostics-preserve-existing-output_47.stderr')),
            ('invalid_53.b', expected_text('diagnostics-preserve-existing-output_47.stderr')),
            ('invalid_54.b', expected_text('diagnostics-preserve-existing-output_48.stderr')),
            ('invalid_55.b', expected_text('diagnostics-preserve-existing-output_49.stderr')),
            ('invalid_56.b', expected_text('diagnostics-preserve-existing-output_50.stderr')),
            ('invalid_57.b', expected_text('diagnostics-preserve-existing-output_51.stderr')),
            ('invalid_58.b', expected_text('diagnostics-preserve-existing-output_52.stderr')),
            ('invalid_59.b', expected_text('diagnostics-preserve-existing-output_52.stderr')),
            ('invalid_60.b', expected_text('diagnostics-preserve-existing-output_53.stderr')),
            ('invalid_61.b', expected_text('diagnostics-preserve-existing-output_53.stderr')),
            ('invalid_62.b', expected_text('diagnostics-preserve-existing-output_54.stderr')),
            ('invalid_63.b', expected_text('diagnostics-preserve-existing-output_55.stderr')),
            ('invalid_64.b', expected_text('diagnostics-preserve-existing-output_56.stderr')),
            ('invalid_65.b', expected_text('diagnostics-preserve-existing-output_57.stderr')),
            ('invalid_66.b', expected_text('diagnostics-preserve-existing-output_58.stderr')),
            ('invalid_67.b', expected_text('diagnostics-preserve-existing-output_59.stderr')),
            ('invalid_68.b', expected_text('diagnostics-preserve-existing-output_60.stderr')),
            ('invalid_69.b', expected_text('diagnostics-preserve-existing-output_61.stderr')),
            ('invalid_70.b', expected_text('diagnostics-preserve-existing-output_62.stderr')),
            ('invalid_71.b', expected_text('diagnostics-preserve-existing-output_63.stderr')),
            ('invalid_72.b', expected_text('diagnostics-preserve-existing-output_64.stderr')),
            ('invalid_73.b', expected_text('diagnostics-preserve-existing-output_65.stderr')),
            ('invalid_74.b', expected_text('diagnostics-preserve-existing-output_66.stderr')),
            ('invalid_75.b', expected_text('diagnostics-preserve-existing-output_67.stderr')),
            ('invalid_76.b', expected_text('diagnostics-preserve-existing-output_68.stderr')),
            ('invalid_77.b', expected_text('diagnostics-preserve-existing-output_69.stderr')),
            ('invalid_78.b', expected_text('diagnostics-preserve-existing-output_69.stderr')),
            ('invalid_79.b', expected_text('diagnostics-preserve-existing-output_70.stderr')),
            ('invalid_80.b', expected_text('diagnostics-preserve-existing-output_70.stderr')),
            ('invalid_81.b', expected_text('diagnostics-preserve-existing-output_71.stderr')),
            ('invalid_82.b', expected_text('diagnostics-preserve-existing-output_72.stderr')),
            ('invalid_83.b', expected_text('diagnostics-preserve-existing-output_73.stderr')),
            ('invalid_84.b', expected_text('diagnostics-preserve-existing-output_74.stderr')),
            ('invalid_85.b', expected_text('diagnostics-preserve-existing-output_75.stderr')),
            ('invalid_86.b', expected_text('diagnostics-preserve-existing-output_76.stderr')),
            ('invalid_87.b', expected_text('diagnostics-preserve-existing-output_77.stderr')),
            ('invalid_88.b', expected_text('diagnostics-preserve-existing-output_77.stderr')),
            ('invalid_89.b', expected_text('diagnostics-preserve-existing-output_78.stderr')),
            ('invalid_90.b', expected_text('diagnostics-preserve-existing-output_79.stderr')),
            ('invalid_91.b', expected_text('diagnostics-preserve-existing-output_80.stderr')),
            ('invalid_92.b', expected_text('diagnostics-preserve-existing-output_80.stderr')),
            ('invalid_93.b', expected_text('diagnostics-preserve-existing-output_81.stderr')),
            ('invalid_94.b', expected_text('diagnostics-preserve-existing-output_82.stderr')),
            ('invalid_95.b', expected_text('diagnostics-preserve-existing-output_83.stderr')),
            ('invalid_96.b', expected_text('diagnostics-preserve-existing-output_84.stderr')),
            ('invalid_97.b', expected_text('diagnostics-preserve-existing-output_85.stderr')),
            ('invalid_98.b', expected_text('diagnostics-preserve-existing-output_86.stderr')),
            ('invalid_99.b', expected_text('diagnostics-preserve-existing-output_87.stderr')),
            ('invalid_100.b', expected_text('diagnostics-preserve-existing-output_88.stderr')),
            ('invalid_101.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
            ('invalid_102.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
            ('invalid_103.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
            ('invalid_104.b', expected_text('diagnostics-preserve-existing-output_89.stderr')),
            ('invalid_105.b', expected_text('diagnostics-preserve-existing-output_90.stderr')),
            ('invalid_106.b', expected_text('diagnostics-preserve-existing-output_24.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/diagnostics-preserve-existing-output' / fixture_name
                self.c.write_text('previous output')
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + location, run.stderr)
                self.assertEqual(self.c.read_text(), 'previous output')

    def test_matbuild_diagnostics(self):
        source = ROOT / 'tests/programs/matbuild-missing-array.b'
        build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn(expected_text('matbuild-diagnostics.stderr', source=source), build.stderr)
        for fixture_name, message in (
            ('matbuild_1.b', expected_text('matbuild-diagnostics_2.stderr')),
            ('matbuild_2.b', expected_text('matbuild-diagnostics_3.stderr')),
            ('matbuild_3.b', expected_text('matbuild-diagnostics_4.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/matbuild-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('matbuild-diagnostics_5.stderr', source=source, message=message).encode(), run.stderr)

    def test_matparse_diagnostics(self):
        source = ROOT / 'tests/programs/matparse-missing-array.b'
        build = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(build.returncode, 0)
        self.assertIn(expected_text('matparse-diagnostics.stderr', source=source), build.stderr)
        for fixture_name, message in (
            ('matparse_1.b', expected_text('matparse-diagnostics_2.stderr')),
            ('matparse_2.b', expected_text('matparse-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/matparse-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('matparse-diagnostics_4.stderr', source=source, message=message).encode(), run.stderr)

    def test_ins_diagnostics(self):
        for name, diagnostic in [
                ('ins_1.b', expected_text('ins-diagnostics.stderr')),
                ('ins_2.b', expected_text('ins-diagnostics_2.stderr')),
                ('ins_3.b', expected_text('ins-diagnostics_3.stderr'))]:
            with self.subTest(source=name):
                source = ROOT / 'tests/programs/array-diagnostics' / name
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + diagnostic, run.stderr)
        source = ROOT / 'tests/programs/array-diagnostics/ins-nonnumeric-index.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('ins-diagnostics_4.stderr', source=source).encode(), run.stderr)

    def test_insert_diagnostics(self):
        for name, message in [
                ('insert_1.b', expected_text('insert-diagnostics.stderr')),
                ('insert_2.b', expected_text('insert-diagnostics_2.stderr'))]:
            with self.subTest(source=name):
                source = ROOT / 'tests/programs/array-diagnostics' / name
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + message, run.stderr)
        source = ROOT / 'tests/programs/array-diagnostics/insert-nonnumeric-index.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('insert-diagnostics_3.stderr', source=source).encode(), run.stderr)

    def test_delete_function_rejects_nonnumeric_index(self):
        source = ROOT / 'tests/programs/array-diagnostics/delete-nonnumeric-index.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('delete-function-rejects-nonnumeric-index.stderr', source=source).encode(), run.stderr)

    def test_extract_rejects_nonnumeric_index(self):
        source = ROOT / 'tests/programs/array-diagnostics/extract-nonnumeric-index.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('extract-rejects-nonnumeric-index.stderr', source=source).encode(), run.stderr)

    def test_del_diagnostics(self):
        for name, diagnostic in [
                ('del_1.b', expected_text('del-diagnostics.stderr')),
                ('del_2.b', expected_text('del-diagnostics_2.stderr')),
                ('del_3.b', expected_text('del-diagnostics_3.stderr'))]:
            with self.subTest(source=name):
                source = ROOT / 'tests/programs/array-diagnostics' / name
                run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(source) + diagnostic, run.stderr)
        source = ROOT / 'tests/programs/array-diagnostics/del-nonnumeric-index.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('del-diagnostics_4.stderr', source=source).encode(), run.stderr)

    def test_exit_status_from_subroutine(self):
        main = ROOT / 'tests/routines/exit-status/main.b'
        sub = ROOT / 'tests/routines/exit-status/finish.b'
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 23, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('exit-status-from-subroutine.stdout'))
        sub = ROOT / 'tests/routines/exit-status/finish-invalid-value.b'
        run = self.run_native(main, sub)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('exit-status-from-subroutine.stderr', sub=sub).encode(), run.stderr)

    def test_stop_and_abort_from_main(self):
        for fixture_name, status, message in (
            ('main_1.b', 0, expected_bytes('stop-and-abort-from-main.stderr')),
            ('main_2.b', 1, b''),
            ('main_3.b', 1, expected_bytes('stop-and-abort-from-main_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/stop-and-abort-from-main' / fixture_name
                run = self.run_native(source)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (status, expected_bytes('stop-and-abort-from-main.stdout'), message))

    def test_stop_and_abort_from_routine(self):
        main = ROOT / 'tests/routines/stop-and-abort/main.b'
        for fixture_name, status, message in (
            ('finish_1.b', 0, expected_bytes('stop-and-abort-from-routine.stderr')),
            ('finish_2.b', 1, expected_bytes('stop-and-abort-from-routine_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                sub = ROOT / 'tests/programs/stop-and-abort-from-routine' / fixture_name
                run = self.run_native(main, sub)
                self.assertEqual((run.returncode, run.stdout, run.stderr), (status, b'', message))

    def test_stop_missing_message_argument(self):
        source = ROOT / 'tests/programs/stop-missing-message-argument.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('stop-missing-message-argument.stderr', source=source), result.stderr)

    def test_mismatched_next_counter(self):
        source = ROOT / 'tests/programs/mismatched-next.b'
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(build.stderr.splitlines(), [
            expected_text('mismatched-next-counter.stderr', source=source),
            expected_text('mismatched-next-counter_2.stderr', source=source),
        ])
        run = subprocess.run([binary], capture_output=True, timeout=5)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('mismatched-next-counter.stdout'))

    def test_loop_exit_control_flow_diagnostics(self):
        binary = self.work / 'program'
        for case_number, keyword in enumerate(('EXIT', 'BREAK'), 1):
            with self.subTest(keyword=keyword):
                source = ROOT / 'tests/programs/loop-exit-control-flow-diagnostics' / f'exit_{case_number}.b'
                run = self.run_native(source)
                self.assertEqual((run.returncode, run.stdout, run.stderr),
                                 (1, b'', expected_text('loop-exit-control-flow-diagnostics.stderr', source=source).encode()))
                source = ROOT / 'tests/programs/loop-exit-control-flow-diagnostics' / f'exit-variant-2_{case_number}.b'
                build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
                self.assertEqual(build.returncode, 0, build.stderr)
                self.assertIn(expected_text('loop-exit-control-flow-diagnostics_2.stderr', source=source, keyword=keyword), build.stderr)
                self.assertEqual(subprocess.check_output([binary]), expected_bytes('loop-exit-control-flow-diagnostics.stdout'))

    def test_scalar_reads_after_loop_check_earlier_iterations(self):
        source = ROOT / 'tests/programs/loop-scalar-read.b'
        binary = self.work / 'loop'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        for limit, expected in (
            ('-1', (0, b'', b'')),
            ('0', (1, b'', expected_text('scalar-reads-after-loop-check-earlier-iterations.stderr', source=source).encode())),
            ('2', (0, expected_bytes('scalar-reads-after-loop-check-earlier-iterations.stdout'), b'')),
            ('3', (0, expected_bytes('scalar-reads-after-loop-check-earlier-iterations_2.stdout'), b'')),
        ):
            with self.subTest(limit=limit):
                run = subprocess.run([binary, limit], capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_continue_outside_loop(self):
        source = ROOT / 'tests/programs/continue-outside-loop.b'
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertIn(expected_text('continue-outside-loop.stderr', source=source), build.stderr)
        self.assertEqual(subprocess.check_output([binary]), expected_bytes('continue-outside-loop.stdout'))

    def test_loop_control_does_not_use_the_gosub_callers_loop(self):
        # The 201015.001 reference emits no jump for either statement here.
        source = ROOT / 'tests/programs/gosub-loop-control.b'
        binary = self.work / 'program'
        build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
        self.assertEqual(build.returncode, 0, build.stderr)
        self.assertEqual(build.stderr.splitlines(), [
            expected_text('loop-control-does-not-use-the-gosub-callers-loop.stderr', source=source),
            expected_text('loop-control-does-not-use-the-gosub-callers-loop_2.stderr', source=source),
        ])
        run = subprocess.run([binary], capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('loop-control-does-not-use-the-gosub-callers-loop.stdout'), b''))

    def test_integer_limits(self):
        for case_number, (text, diagnostic) in enumerate([('9223372036854775807', expected_text('integer-limits.stderr')),
                                 ('"nan"', expected_text('integer-limits_2.stderr'))], 1):
            with self.subTest(text=text):
                source = ROOT / 'tests/programs/integer-limits' / f'numbers_{case_number}.b'
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(diagnostic.encode(), run.stderr)
                self.assertIn(expected_text('integer-limits_3.stderr', source=source, value_2=len(text) + 6).encode(), run.stderr)

    def test_logical_function_calls(self):
        main = ROOT / 'tests/routines/logical-calls/main.b'
        function = ROOT / 'tests/routines/logical-calls/bump.b'
        run = self.run_native(main, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('logical-function-calls.stdout'))
        main = ROOT / 'tests/routines/logical-calls/unassigned.b'
        run = subprocess.run([CLI, main, function, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('logical-function-calls.stderr', main=main), run.stderr)

    def test_conditional_expression_calls(self):
        main = ROOT / 'tests/routines/conditional-calls/main.b'
        function = ROOT / 'tests/routines/conditional-calls/bump.b'
        run = self.run_native(main, function)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected_bytes('conditional-expression-calls.stdout'), b''))

        main = ROOT / 'tests/routines/conditional-calls/unassigned.b'
        run = subprocess.run([CLI, main, function, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('conditional-expression-calls.stderr', main=main), run.stderr)

    def test_conditional_expression_requires_else(self):
        source = ROOT / 'tests/programs/conditional-missing-else.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('conditional-expression-requires-else.stderr', source=source), result.stderr)

    def test_precision_call_scope(self):
        sources = ROOT / 'tests/routines/precision-scope'
        run = self.run_native(sources / 'main.b', sources / 'change.b', sources / 'local.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('precision-call-scope.stdout'))

    def test_invalid_precision(self):
        for fixture_name in (
            'bad_1.b',
            'bad_2.b',
            'bad_3.b',
            'bad_4.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/invalid-precision' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('invalid-precision.stderr', source=source).encode(), run.stderr)

    def test_locate_diagnostics(self):
        for fixture_name, message in (
            ('main_1.b', expected_text('locate-diagnostics.stderr')),
            ('main_2.b', expected_text('locate-diagnostics_2.stderr')),
            ('main_3.b', expected_text('locate-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                main = ROOT / 'tests/programs/locate-diagnostics' / fixture_name
                run = self.run_native(main)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('locate-diagnostics_4.stderr', main=main, message=message).encode(), run.stderr)

    def test_locate_subvalue_start_diagnostics(self):
        main = ROOT / 'tests/programs/locate-zero-subvalue.b'
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('locate-subvalue-start-diagnostics.stderr', main=main).encode(), run.stderr)
        main = ROOT / 'tests/programs/locate-duplicate-start.b'
        result = subprocess.run([CLI, main, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('locate-subvalue-start-diagnostics_2.stderr', main=main), result.stderr)

    def test_sum_overflow_reports_call_site(self):
        source = ROOT / 'tests/programs/sum-overflow.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('sum-overflow-reports-call-site.stderr', source=source).encode(), run.stderr)

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

    def test_unique_key_returns_distinct_uuid_strings(self):
        run = self.run_native(ROOT / 'tests/programs/unique-key.b')
        self.assertEqual((run.returncode, run.stderr), (0, b''))
        values = run.stdout.splitlines()
        self.assertEqual(len(values), 5)
        self.assertEqual(len(set(values)), 5)
        for value in values:
            self.assertRegex(value, rb'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$')

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

    def test_iconv_diagnostics(self):
        cases = [
            ("'20121231', 'MD2'", expected_text('iconv-diagnostics.stderr')),
            ("'24:00', 'MT'", expected_text('iconv-diagnostics_2.stderr')),
            ("'0:00 AM', 'MTS'", expected_text('iconv-diagnostics_2.stderr')),
            ("'2012123', 'D'", expected_text('iconv-diagnostics_3.stderr')),
            ("'20121231x', 'D'", expected_text('iconv-diagnostics_3.stderr')),
            ("'19000229', 'D4'", expected_text('iconv-diagnostics_4.stderr')),
            ("'20120431', 'D'", expected_text('iconv-diagnostics_4.stderr')),
            ("'20121301', 'D'", expected_text('iconv-diagnostics_4.stderr')),
            ("'00000101', 'D'", expected_text('iconv-diagnostics_4.stderr')),
        ]
        for case_number, (args, message) in enumerate(cases, 1):
            with self.subTest(args=args):
                source = ROOT / 'tests/programs/iconv-diagnostics' / f'date_{case_number}.b'
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('iconv-diagnostics_5.stderr', source=source, message=message).encode(), run.stderr)

    def test_iconvs_empty_mask_diagnostic(self):
        source = ROOT / 'tests/programs/iconvs-empty-mask.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('iconvs-empty-mask-diagnostic.stderr', source=source).encode(), result.stderr)

    def test_oconvs_empty_mask_diagnostic(self):
        source = ROOT / 'tests/programs/oconvs-empty-mask.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('oconvs-empty-mask-diagnostic.stderr', source=source).encode(), result.stderr)

    def test_oconv_diagnostics(self):
        for fixture_name, message in (
            ('date_1.b', expected_text('oconv-diagnostics.stderr')),
            ('date_2.b', expected_text('oconv-diagnostics_2.stderr')),
            ('date_3.b', expected_text('oconv-diagnostics_2.stderr')),
            ('date_4.b', expected_text('oconv-diagnostics_2.stderr')),
            ('date_5.b', expected_text('oconv-diagnostics_3.stderr')),
            ('date_6.b', expected_text('oconv-diagnostics_4.stderr')),
            ('date_7.b', expected_text('oconv-diagnostics_5.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/oconv-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('oconv-diagnostics_6.stderr', source=source, message=message).encode(), run.stderr)

    def test_str_repetition_diagnostics(self):
        for fixture_name, message in (
            ('repeat_1.b', expected_text('str-repetition-diagnostics.stderr')),
            ('repeat_2.b', expected_text('str-repetition-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/str-repetition-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('str-repetition-diagnostics_3.stderr', source=source, message=message).encode(), run.stderr)

    def test_spaces_diagnostics(self):
        for fixture_name, message in (
            ('spaces_1.b', expected_text('spaces-diagnostics.stderr')),
            ('spaces_2.b', expected_text('spaces-diagnostics.stderr')),
            ('spaces_3.b', expected_text('spaces-diagnostics.stderr')),
            ('spaces_4.b', expected_text('spaces-diagnostics.stderr')),
            ('spaces_5.b', expected_text('spaces-diagnostics_2.stderr')),
            ('spaces_6.b', expected_text('spaces-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/spaces-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('spaces-diagnostics_4.stderr', source=source, message=message).encode(), result.stderr)

    def test_left_right_require_numeric_length(self):
        for fixture_name in (
            'length_1.b',
            'length_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/left-right-require-numeric-length' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('left-right-require-numeric-length.stderr', source=source).encode(), run.stderr)

    def test_suffix_requires_numeric_length(self):
        source = ROOT / 'tests/programs/suffix-nonnumeric-length.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('suffix-requires-numeric-length.stderr', source=source).encode(), run.stderr)

    def test_counts_requires_two_arguments(self):
        for fixture_name in (
            'counts_1.b',
            'counts_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/counts-requires-two-arguments' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('counts-requires-two-arguments.stderr', source=source), result.stderr)

    def test_col_positions_require_no_arguments(self):
        for case_number, name in enumerate(('COL1', 'COL2'), 1):
            with self.subTest(name=name):
                source = ROOT / 'tests/programs/col-positions-require-no-arguments' / f'field-positions_{case_number}.b'
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('col-positions-require-no-arguments.stderr', source=source, value_2=name), result.stderr)

    def test_delimited_bracket_assignment_diagnostics(self):
        for fixture_name, message in (
            ('fields_1.b', expected_text('delimited-bracket-assignment-diagnostics.stderr')),
            ('fields_2.b', expected_text('delimited-bracket-assignment-diagnostics_2.stderr')),
            ('fields_3.b', expected_text('delimited-bracket-assignment-diagnostics_3.stderr')),
            ('fields_4.b', expected_text('delimited-bracket-assignment-diagnostics_4.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/delimited-bracket-assignment-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr, expected_text('delimited-bracket-assignment-diagnostics_5.stderr', source=source, message=message).encode())

    def test_jbasecoredump_requires_an_application_snapshot_backend(self):
        source = ROOT / 'tests/programs/jbasecoredump-missing-backend.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (1, expected_bytes('jbasecoredump-requires-an-application-snapshot-backend.stdout'),
                          expected_text('jbasecoredump-requires-an-application-snapshot-backend.stderr', source=source).encode()))
        self.assertEqual(list(self.work.glob('JBASECOREDUMP*')), [])

        for fixture_name in (
            'snapshot_1.b',
            'snapshot_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/jbasecoredump-requires-an-application-snapshot-backend' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('jbasecoredump-requires-an-application-snapshot-backend_2.stderr', source=source), result.stderr)

    def test_itype_requires_backend_only_when_evaluation_is_reached(self):
        source = ROOT / 'tests/programs/itype-missing-backend.b'
        result = self.run_native(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (1, expected_bytes('itype-requires-backend-only-when-evaluation-is-reached.stdout'),
                          expected_text('itype-requires-backend-only-when-evaluation-is-reached.stderr', source=source).encode()))

    def test_xml_transforms_require_a_backend_when_reached(self):
        for fixture_name, call in (
            ('xml_1.b', "XMLTOXML('<doc/>', '', Code)"),
            ('xml_2.b', "XMLTODYN('<array/>', '', Codes(1))"),
            ('xml_3.b', "XMLTODYN('<array/>', '')"),
            ('xml_4.b', "DYNTOXML('a':@FM:'b', '', Code)"),
            ('xml_5.b', "DYNTOXML('a':@FM:'b', '', Codes(1))"),
            ('xml_6.b', "DYNTOXML('a':@FM:'b', '')"),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/xml-transforms-require-a-backend-when-reached' / fixture_name
                result = self.run_native(source)
                name = call.split('(', 1)[0]
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (1, expected_bytes('xml-transforms-require-a-backend-when-reached.stdout'), expected_text('xml-transforms-require-a-backend-when-reached.stderr', source=source, value_2=name).encode()))

    def test_xml_transform_argument_diagnostics(self):
        for case_number, (call, marker, message) in enumerate((
            ("XMLTODYN('<array/>')", ')', expected_text('xml-transform-argument-diagnostics.stderr')),
            ("XMLTOXML('<doc/>', '', 0)", '0', expected_text('xml-transform-argument-diagnostics_2.stderr')),
            ("XMLTODYN('<array/>', '', Code<1>)", '<1>', expected_text('xml-transform-argument-diagnostics_3.stderr')),
            ("XMLTOXML('<doc/>', '', Code, Extra)", ', Extra', expected_text('xml-transform-argument-diagnostics_3.stderr')),
            ("DYNTOXML('a', '', 0)", '0', expected_text('xml-transform-argument-diagnostics_2.stderr')),
        ), 1):
            with self.subTest(call=call):
                statement = f'CRT {call}'
                source = ROOT / 'tests/programs/xml-transform-argument-diagnostics' / f'xml_{case_number}.b'
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('xml-transform-argument-diagnostics_4.stderr', source=source, value_2=statement.rindex(marker) + 1, message=message), result.stderr)

    def test_indices_requires_backend_only_when_a_query_is_reached(self):
        for fixture_name in (
            'indices_1.b',
            'indices_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/indices-requires-backend-only-when-a-query-is-reached' / fixture_name
                result = self.run_native(source, options=('--memory-file', 'BOOKS'))
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, expected_bytes('indices-requires-backend-only-when-a-query-is-reached.stdout'))
                self.assertEqual(
                    result.stderr, expected_text('indices-requires-backend-only-when-a-query-is-reached.stderr', source=source).encode()
                )

    def test_indices_requires_a_file_variable(self):
        source = ROOT / 'tests/programs/indices-requires-variable.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('indices-requires-a-file-variable.stderr', source=source))

    def test_concatenation_with_an_omitted_right_operand(self):
        source = ROOT / 'tests/routines/concat-omitted-operand/main.b'
        show = ROOT / 'tests/routines/concat-omitted-operand/show.b'
        result = self.run_native(source, show)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('concatenation-with-an-omitted-right-operand.stdout'), b''))

    def test_period_label_diagnostics(self):
        for fixture_name, location in (
            ('period_1.b', expected_text('period-label-diagnostics.stderr')),
            ('period_2.b', expected_text('period-label-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/period-label-diagnostics' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(source) + location, result.stderr)

    def test_clear_resets_local_storage_and_preserves_shared_slots(self):
        main = ROOT / 'tests/routines/clear-storage/main.b'
        reset = ROOT / 'tests/routines/clear-storage/reset.b'
        result = self.run_native(main, reset)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('clear-resets-local-storage-and-preserves-shared-slots.stdout'), b''))

    def test_clear_requires_a_path_that_initializes_the_local(self):
        source = ROOT / 'tests/programs/clear-unassigned-local.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('clear-requires-a-path-that-initializes-the-local.stderr', source=source))

    def test_concatenation_requires_a_left_operand(self):
        source = ROOT / 'tests/programs/concat-missing-left.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(
            result.stderr, expected_text('concatenation-requires-a-left-operand.stderr', source=source)
        )

    def test_comparison_signs_keep_reference_spacing_rules(self):
        for fixture_name, column in (
            ('compare_1.b', 7),
            ('compare_2.b', 9),
            ('compare_3.b', 9),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/comparison-signs-keep-reference-spacing-rules' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(
                    result.stderr,
                    expected_text('comparison-signs-keep-reference-spacing-rules.stderr', source=source, column=column)
                )

    def test_single_index_substring_assignment_diagnostics(self):
        source = ROOT / 'tests/programs/substring-nonnumeric-index.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('single-index-substring-assignment-diagnostics.stderr', source=source).encode(), result.stderr)

        source = ROOT / 'tests/programs/substring-invalid-assignment.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('single-index-substring-assignment-diagnostics_2.stderr', source=source), result.stderr)

    def test_substrings_requires_numeric_bounds(self):
        for fixture_name in (
            'substrings_1.b',
            'substrings_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/substrings-requires-numeric-bounds' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('substrings-requires-numeric-bounds.stderr', source=source).encode(), run.stderr)

    def test_splice_reuse_scalar(self):
        source = ROOT / 'tests/routines/splice-reuse/main.b'
        bump = ROOT / 'tests/routines/splice-reuse/bump.b'
        run = self.run_native(source, bump)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('splice-reuse-scalar.stdout'))

        source = ROOT / 'tests/programs/splice-reuse-array.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('splice-reuse-scalar.stderr', source=source).encode(), run.stderr)

    def test_eqs_reuse_requires_scalar(self):
        source = ROOT / 'tests/programs/eqs-reuse-array.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('eqs-reuse-requires-scalar.stderr', source=source).encode(), run.stderr)

    def test_ordered_array_comparisons(self):
        source = ROOT / 'tests/routines/ordered-array-comparisons/main.b'
        bump = ROOT / 'tests/routines/ordered-array-comparisons/bump.b'
        result = self.run_native(source, bump)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('ordered-array-comparisons.stdout'), b''))

    def test_ordered_array_comparison_rejects_reuse_of_an_array(self):
        source = ROOT / 'tests/programs/les-reuse-array.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b'')
        self.assertEqual(result.stderr, expected_text('ordered-array-comparison-rejects-reuse-of-an-array.stderr', source=source).encode())

    def test_compare_invalid_justification(self):
        source = ROOT / 'tests/programs/compare-invalid-justification.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('compare-invalid-justification.stderr', source=source).encode(), run.stderr)

    def test_fold_invalid_width(self):
        for fixture_name in (
            'fold_1.b',
            'fold_2.b',
            'fold_3.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/fold-invalid-width' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('fold-invalid-width.stderr', source=source).encode(), run.stderr)

    def test_fmts_invalid_mask(self):
        for fixture_name, mask in (
            ('fmts_1.b', ''),
            ('fmts_2.b', 'R?'),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/fmts-invalid-mask' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('fmts-invalid-mask.stderr', source=source, mask=mask).encode(), run.stderr)

    def test_dround_diagnostics(self):
        for fixture_name, diagnostic in (
            ('dround_1.b', expected_text('dround-diagnostics.stderr')),
            ('dround_2.b', expected_text('dround-diagnostics_2.stderr')),
            ('dround_3.b', expected_text('dround-diagnostics_2.stderr')),
            ('dround_4.b', expected_text('dround-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/dround-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('dround-diagnostics_3.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

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

    def test_callonexit_dispatches_linked_callbacks(self):
        save = ROOT / 'tests/routines/exit-callbacks/save.b'
        show = ROOT / 'tests/routines/exit-callbacks/show.b'
        wrong = ROOT / 'tests/routines/exit-callbacks/wrong.b'
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
        for case_number, (ending, status) in enumerate((('', 0), ('STOP', 0), ('EXIT(7)', 7), ('ABORT', 1), ('DEBUG', 1)), 1):
            with self.subTest(ending=ending):
                source = ROOT / 'tests/routines/callonexit-dispatches-linked-callbacks' / f'exit_{case_number}.b'
                result = self.run_native(source, save, show, wrong)
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertEqual(result.stdout, expected_bytes('callonexit-dispatches-linked-callbacks.stdout'))
                if ending == 'DEBUG':
                    self.assertIn(expected_bytes('callonexit-dispatches-linked-callbacks.stderr'), result.stderr)
                else:
                    self.assertEqual(result.stderr, b'')

    def test_debug_reports_location_only_when_reached(self):
        source = ROOT / 'tests/programs/debug-missing-backend.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, expected_bytes('debug-reports-location-only-when-reached.stdout'))
        self.assertEqual(result.stderr, expected_text('debug-reports-location-only-when-reached.stderr', source=source).encode())

    def test_callj_reports_missing_backend_only_when_reached(self):
        source = ROOT / 'tests/programs/callj-missing-backend.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('callj-reports-missing-backend-only-when-reached.stdout'))
        self.assertEqual(result.stderr, expected_text('callj-reports-missing-backend-only-when-reached.stderr', source=source).encode())

    def test_callj_requires_setting(self):
        source = ROOT / 'tests/programs/callj-missing-setting.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('callj-requires-setting.stderr', source=source))

    def test_transactions_report_missing_backend_at_the_call(self):
        statements = (
            ('TRANSTART', "TRANSTART ELSE CRT 'failure'"),
            ('TRANSTART', "TRANSTART SYNC THEN CRT 'success'"),
            ('TRANSTART', "TRANSTART SYNC 'start':Note THEN CRT 'success' ELSE CRT 'failure'"),
            ('TRANSEND', "TRANSEND Note THEN\n    CRT 'success'\nEND ELSE CRT 'failure'"),
            ('TRANSABORT', "TRANSABORT 'rollback' ELSE CRT 'failure'"),
        )
        for case_number, (keyword, statement) in enumerate(statements, 1):
            with self.subTest(statement=statement):
                source = ROOT / 'tests/programs/transactions-report-missing-backend-at-the-call' / f'transactions_{case_number}.b'
                result = self.run_native(source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, expected_bytes('transactions-report-missing-backend-at-the-call.stdout'))
                self.assertEqual(
                    result.stderr, expected_text('transactions-report-missing-backend-at-the-call.stderr', source=source, keyword=keyword).encode()
                )

    def test_transactions_require_a_conditional_arm(self):
        source = ROOT / 'tests/programs/transtart-missing-arm.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('transactions-require-a-conditional-arm.stderr', source=source))

    def test_transaction_dialect_reports_missing_backend(self):
        source = ROOT / 'tests/programs/transaction-dialect.b'
        binary = self.work / 'transactions'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        run = subprocess.run([binary, 'skip'], capture_output=True, timeout=5)
        self.assertEqual((run.returncode, run.stdout, run.stderr), (0, expected_bytes('transaction-dialect-reports-missing-backend.stdout'), b''))
        for operation, line in (('start', 4), ('commit', 6), ('abort', 8)):
            with self.subTest(operation=operation):
                run = subprocess.run([binary, operation], capture_output=True, timeout=5)
                error = expected_text('transaction-dialect-reports-missing-backend.stderr', source=source, line=line, value_3=operation.upper())
                self.assertEqual((run.returncode, run.stdout, run.stderr), (1, b'', error.encode()))

    def test_transaction_start_requires_a_conditional_arm(self):
        source = ROOT / 'tests/programs/transaction-start-missing-arm.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual((run.returncode, run.stderr), (1, expected_text('transaction-start-requires-a-conditional-arm.stderr', source=source)))

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

    def test_smul_diagnostics(self):
        for fixture_name, diagnostic in (
            ('smul_1.b', expected_text('smul-diagnostics.stderr')),
            ('smul_2.b', expected_text('smul-diagnostics.stderr')),
            ('smul_3.b', expected_text('smul-diagnostics_2.stderr')),
            ('smul_4.b', expected_text('smul-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/smul-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('smul-diagnostics_3.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_sdiv_diagnostics(self):
        for fixture_name, diagnostic in (
            ('sdiv_1.b', expected_text('sdiv-diagnostics.stderr')),
            ('sdiv_2.b', expected_text('sdiv-diagnostics.stderr')),
            ('sdiv_3.b', expected_text('sdiv-diagnostics_2.stderr')),
            ('sdiv_4.b', expected_text('sdiv-diagnostics_3.stderr')),
            ('sdiv_5.b', expected_text('sdiv-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/sdiv-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('sdiv-diagnostics_4.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_adds_diagnostics(self):
        for fixture_name, diagnostic in (
            ('adds_1.b', expected_text('adds-diagnostics.stderr')),
            ('adds_2.b', expected_text('adds-diagnostics_2.stderr')),
            ('adds_3.b', expected_text('adds-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/adds-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_infix_reuse_requires_scalar(self):
        source = ROOT / 'tests/programs/infix-reuse-requires-scalar.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('infix-reuse-requires-scalar.stderr', source=source).encode(),
                      result.stderr)

    def test_muls_diagnostics(self):
        for fixture_name, diagnostic in (
            ('muls_1.b', expected_text('muls-diagnostics.stderr')),
            ('muls_2.b', expected_text('muls-diagnostics_2.stderr')),
            ('muls_3.b', expected_text('muls-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/muls-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_divs_substitutes_zero_for_zero_divisors(self):
        source = ROOT / 'tests/programs/divs-substitutes-zero-for-zero-divisors.b'
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('divs-substitutes-zero-for-zero-divisors.stdout'))
        warning = expected_text('divs-substitutes-zero-for-zero-divisors.stderr', source=source)
        self.assertEqual(run.stderr, warning.encode() * 2)

    def test_infix_reuse_division_reports_invalid_operands(self):
        for case_number, (expression, marker, message) in enumerate((
            ("(4:@VM:6) / REUSE(0)", '/', expected_text('infix-reuse-division-reports-invalid-operands.stderr')),
            ("REUSE(8) / (2:@VM:0)", '/', expected_text('infix-reuse-division-reports-invalid-operands.stderr')),
            ("REUSE(3:@FM:4) / 2", 'REUSE', expected_text('infix-reuse-division-reports-invalid-operands_2.stderr')),
        ), 1):
            with self.subTest(expression=expression):
                statement = f'CRT {expression}'
                source = ROOT / 'tests/programs/infix-reuse-division-reports-invalid-operands' / f'reuse_{case_number}.b'
                result = self.run_native(source)
                self.assertEqual((result.returncode, result.stdout, result.stderr),
                                 (1, b'', expected_text('infix-reuse-division-reports-invalid-operands_3.stderr', source=source, value_2=statement.index(marker) + 1, message=message).encode()))

    def test_divs_diagnostics(self):
        for fixture_name, diagnostic in (
            ('divs_1.b', expected_text('divs-diagnostics.stderr')),
            ('divs_2.b', expected_text('divs-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/divs-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_subs_diagnostics(self):
        for fixture_name, diagnostic in (
            ('subs_1.b', expected_text('subs-diagnostics.stderr')),
            ('subs_2.b', expected_text('subs-diagnostics.stderr')),
            ('subs_3.b', expected_text('subs-diagnostics_2.stderr')),
            ('subs_4.b', expected_text('subs-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/subs-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + diagnostic).encode(), run.stderr)

    def test_ln_diagnostics(self):
        for fixture_name, message in (
            ('ln_1.b', expected_text('ln-diagnostics.stderr')),
            ('ln_2.b', expected_text('ln-diagnostics_2.stderr')),
            ('ln_3.b', expected_text('ln-diagnostics_2.stderr')),
            ('ln_4.b', expected_text('ln-diagnostics_3.stderr')),
            ('ln_5.b', expected_text('ln-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/ln-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('ln-diagnostics_4.stderr', source=source, message=message).encode(), run.stderr)

    def test_exp_diagnostics(self):
        for fixture_name, message in (
            ('exp_1.b', expected_text('exp-diagnostics.stderr')),
            ('exp_2.b', expected_text('exp-diagnostics_2.stderr')),
            ('exp_3.b', expected_text('exp-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/exp-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('exp-diagnostics_4.stderr', source=source, message=message).encode(), run.stderr)

    def test_sqrt_diagnostics(self):
        for fixture_name, message in (
            ('sqrt_1.b', expected_text('sqrt-diagnostics.stderr')),
            ('sqrt_2.b', expected_text('sqrt-diagnostics_2.stderr')),
            ('sqrt_3.b', expected_text('sqrt-diagnostics_3.stderr')),
            ('sqrt_4.b', expected_text('sqrt-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/sqrt-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('sqrt-diagnostics_4.stderr', source=source, message=message).encode(), run.stderr)

    def test_power_domain_and_diagnostics(self):
        for fixture_name, column, message, continues in (
            ('power_1.b', 5, expected_text('power-domain-and-diagnostics.stderr'), True),
            ('power_2.b', 7, expected_text('power-domain-and-diagnostics_2.stderr'), False),
            ('power_3.b', 7, expected_text('power-domain-and-diagnostics_3.stderr'), False),
            ('power_4.b', 5, expected_text('power-domain-and-diagnostics_4.stderr'), False),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/power-domain-and-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertEqual(run.returncode == 0, continues)
                self.assertEqual(run.stdout, b'0\ndone\n' if continues else b'')
                self.assertIn(expected_text('power-domain-and-diagnostics_5.stderr', source=source, column=column, message=message).encode(), run.stderr)

    def test_randomize_wrong_argument_count(self):
        source = ROOT / 'tests/programs/randomize-wrong-argument-count.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('randomize-wrong-argument-count.stderr', source=source), result.stderr)

    def test_rnd_invalid_bound(self):
        for fixture_name, diagnostic in (
            ('rnd_1.b', expected_text('rnd-invalid-bound.stderr')),
            ('rnd_2.b', expected_text('rnd-invalid-bound.stderr')),
            ('rnd_3.b', expected_text('rnd-invalid-bound_2.stderr')),
            ('rnd_4.b', expected_text('rnd-invalid-bound_3.stderr')),
            ('rnd_5.b', expected_text('rnd-invalid-bound_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/rnd-invalid-bound' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('rnd-invalid-bound_4.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_bitxor_diagnostics(self):
        for fixture_name in (
            'bitxor_1.b',
            'bitxor_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/bitxor-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('bitxor-diagnostics.stderr', source=source).encode(),
                              result.stderr)

        source = ROOT / 'tests/programs/bitxor-diagnostics/bitxor-variant-2.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('bitxor-diagnostics_2.stderr', source=source), result.stderr)

    def test_cipher_diagnostics(self):
        fixtures = ROOT / 'tests/programs/cipher-diagnostics'
        for case_number, function in enumerate(('ENCRYPT', 'DECRYPT'), 1):
            with self.subTest(function=function):
                for method in (4, 5):
                    with self.subTest(method=method):
                        source = fixtures / f'{function.lower()}-{method}.b'
                        result = self.run_native(source)
                        self.assertEqual((result.returncode, result.stdout), (1, expected_bytes('cipher-diagnostics.stdout')))
                        self.assertEqual(result.stderr,
                                         expected_text('cipher-diagnostics.stderr', source=source, function=function).encode())

                source = fixtures / f'crypt_{case_number}.b'
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, expected_text('cipher-diagnostics_2.stderr', source=source, function=function))

    def test_hexadecimal_conversion_diagnostics(self):
        for fixture_name in (
            'hex_1.b',
            'hex_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/hexadecimal-conversion-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('hexadecimal-conversion-diagnostics.stderr', source=source).encode(), result.stderr)
        for fixture_name, function in (
            ('hex-variant-2_1.b', 'DTX'),
            ('hex-variant-2_2.b', 'XTD'),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/hexadecimal-conversion-diagnostics' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('hexadecimal-conversion-diagnostics_2.stderr', source=source, function=function), result.stderr)

    def test_mod_requires_numeric_operands(self):
        for fixture_name, name in (
            ('mod_1.b', 'MOD'),
            ('mod_2.b', 'MOD'),
            ('mod_3.b', 'REM'),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/mod-requires-numeric-operands' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('mod-requires-numeric-operands.stderr', source=source, value_2=name).encode(), run.stderr)

    def test_trim_diagnostics(self):
        for fixture_name, message in (
            ('trim_1.b', expected_text('trim-diagnostics.stderr')),
            ('trim_2.b', expected_text('trim-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/trim-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('trim-diagnostics_3.stderr', source=source, message=message).encode(), run.stderr)

    def test_find_diagnostics(self):
        for fixture_name, error in (
            ('find_1.b', expected_text('find-diagnostics.stderr')),
            ('find_2.b', expected_text('find-diagnostics_2.stderr')),
            ('find_3.b', expected_text('find-diagnostics_3.stderr')),
        ):
            source = ROOT / 'tests/programs/find-diagnostics' / fixture_name
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('find-diagnostics_4.stderr', source=source, error=error), run.stderr)
        for case_number, keyword in enumerate(('FIND', 'FINDSTR'), 1):
            source = ROOT / 'tests/programs/find-diagnostics' / f'find-variant-2_{case_number}.b'
            run = self.run_native(source)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('find-diagnostics_5.stderr', source=source, keyword=keyword).encode(),
                          run.stderr)

    def test_swap_diagnostics(self):
        source = ROOT / 'tests/programs/swap-diagnostics/swap.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('swap-diagnostics.stderr', source=source).encode(), result.stderr)
        source = ROOT / 'tests/programs/swap-diagnostics/swap-variant-2.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('swap-diagnostics_2.stderr', source=source).encode(),
                      result.stderr)

    def test_ereplace_diagnostics(self):
        source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('ereplace-diagnostics.stderr', source=source).encode(), result.stderr)
        source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace-variant-2.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('ereplace-diagnostics_2.stderr', source=source).encode(),
                      result.stderr)

    def test_change_diagnostics(self):
        for fixture_name, error in (
            ('change_1.b', expected_text('change-diagnostics.stderr')),
            ('change_2.b', expected_text('change-diagnostics_2.stderr')),
        ):
            source = ROOT / 'tests/programs/change-diagnostics' / fixture_name
            run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('change-diagnostics_3.stderr', source=source, error=error), run.stderr)
        source = ROOT / 'tests/programs/change-diagnostics/change-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('change-diagnostics_4.stderr', source=source).encode(), run.stderr)

    def test_string_mutations_check_conditionally_assigned_targets(self):
        binary = self.work / 'mutate'
        for case_number, (statement, expected) in enumerate((
            ("CONVERT 'a' TO 'x' IN Value", expected_bytes('string-mutations-check-conditionally-assigned-targets.stdout')),
            ("CHANGE 'aa' TO 'x' IN Value<2>", expected_bytes('string-mutations-check-conditionally-assigned-targets_2.stdout')),
        ), 1):
            with self.subTest(statement=statement):
                source = ROOT / 'tests/programs/string-mutations-check-conditionally-assigned-targets' / f'mutate_{case_number}.b'
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                               env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
                found = subprocess.run([binary, 'found'], capture_output=True, timeout=5)
                self.assertEqual((found.returncode, found.stdout, found.stderr), (0, expected, b''))
                missing = subprocess.run([binary, 'missing'], capture_output=True, timeout=5)
                column = statement.index('Value') + 1
                self.assertEqual((missing.returncode, missing.stdout, missing.stderr),
                                 (1, b'', expected_text('string-mutations-check-conditionally-assigned-targets.stderr', source=source, column=column).encode()))

    def test_neg_substitutes_zero(self):
        source = ROOT / 'tests/programs/neg-substitutes-zero.b'
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('neg-substitutes-zero.stdout'))
        self.assertEqual(run.stderr, expected_text('neg-substitutes-zero.stderr', source=source).encode())

    def test_negs_warns_for_nonnumeric_elements(self):
        source = ROOT / 'tests/programs/negs-warns-for-nonnumeric-elements.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('negs-warns-for-nonnumeric-elements.stdout'))
        warning = expected_text('negs-warns-for-nonnumeric-elements.stderr', source=source)
        self.assertEqual(result.stderr, warning.encode() * 2)

    def test_abs_diagnostics(self):
        source = ROOT / 'tests/programs/abs-diagnostics/abs.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('abs-diagnostics.stderr', source=source).encode(), run.stderr)
        source = ROOT / 'tests/programs/abs-diagnostics/abs-variant-2.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('abs-diagnostics_2.stderr', source=source), run.stderr)

    def test_abss_diagnostics(self):
        source = ROOT / 'tests/programs/abss-diagnostics.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('abss-diagnostics.stderr', source=source).encode(), run.stderr)

    def test_implicit_format_reports_uninitialized_mask_at_read(self):
        source = ROOT / 'tests/programs/implicit-format-reports-uninitialized-mask-at-read.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('implicit-format-reports-uninitialized-mask-at-read.stderr', source=source).encode(), run.stderr)

    def test_fmt_diagnostics(self):
        for case_number, mask in enumerate(['D4/', 'R20', 'R%', "3'xx'R", 'R2,', '0T'], 1):
            with self.subTest(mask=mask):
                source = ROOT / 'tests/programs/fmt-diagnostics' / f'fmt_{case_number}.b'
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('fmt-diagnostics.stderr', source=source, mask=mask).encode(), run.stderr)

    def test_index_diagnostics(self):
        source = ROOT / 'tests/programs/index-diagnostics/index.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('index-diagnostics.stderr', source=source), result.stderr)
        source = ROOT / 'tests/programs/index-diagnostics/index-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('index-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_division_by_zero(self):
        source = ROOT / 'tests/programs/division-by-zero.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('division-by-zero.stderr', source=source).encode(), run.stderr)

    def test_div_requires_nonzero_numeric_operands(self):
        for fixture_name, diagnostic in (
            ('div_1.b', expected_text('div-requires-nonzero-numeric-operands.stderr')),
            ('div_2.b', expected_text('div-requires-nonzero-numeric-operands_2.stderr')),
            ('div_3.b', expected_text('div-requires-nonzero-numeric-operands_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/div-requires-nonzero-numeric-operands' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('div-requires-nonzero-numeric-operands_3.stderr', source=source, diagnostic=diagnostic).encode(), run.stderr)

    def test_increment_and_decrement_expression_values(self):
        source = ROOT / 'tests/programs/increment-and-decrement-expression-values/step.b'
        routine = ROOT / 'tests/programs/increment-and-decrement-expression-values/show-steps.b'
        result = self.run_native(source, routine)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('increment-and-decrement-expression-values.stdout'), b''))

    def test_increment_and_decrement_diagnostics(self):
        for fixture_name, message in (
            ('step_1.b', expected_text('increment-and-decrement-diagnostics.stderr')),
            ('step_2.b', expected_text('increment-and-decrement-diagnostics_2.stderr')),
            ('step_3.b', expected_text('increment-and-decrement-diagnostics_3.stderr')),
            ('step_4.b', expected_text('increment-and-decrement-diagnostics_4.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/increment-and-decrement-diagnostics' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('increment-and-decrement-diagnostics_5.stderr', source=source, message=message), result.stderr)

        source = ROOT / 'tests/programs/increment-and-decrement-diagnostics/step-variant-2.b'
        result = self.run_native(source)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('increment-and-decrement-diagnostics_6.stderr', source=source).encode(), result.stderr)

    def test_spaced_concatenating_assignment_requires_initial_value(self):
        source = ROOT / 'tests/programs/spaced-concatenating-assignment-requires-initial-value.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('spaced-concatenating-assignment-requires-initial-value.stderr', source=source), result.stderr)

    def test_compound_division_by_zero(self):
        source = ROOT / 'tests/programs/compound-division-by-zero.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('compound-division-by-zero.stderr', source=source).encode(), run.stderr)

    def test_compound_assignment_checks_conditionally_assigned_target(self):
        binary = self.work / 'compound'
        for fixture_name, expected in (
            ('compound_1.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target.stdout')),
            ('compound_2.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target_2.stdout')),
            ('compound_3.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target_3.stdout')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/compound-assignment-checks-conditionally-assigned-target' / fixture_name
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                               env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
                hit = subprocess.run([binary, 'hit'], capture_output=True, timeout=5)
                self.assertEqual((hit.returncode, hit.stdout, hit.stderr), (0, expected, b''))
                miss = subprocess.run([binary, 'miss'], capture_output=True, timeout=5)
                self.assertEqual((miss.returncode, miss.stdout, miss.stderr),
                                 (1, b'', expected_text('compound-assignment-checks-conditionally-assigned-target.stderr', source=source).encode()))

    def test_external_subroutine(self):
        directory = ROOT / 'tests/routines'
        run = self.run_native(directory / 'caller.b', directory / 'get.status.b')
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('external-subroutine.stdout'))

    def test_insert_locations(self):
        fixtures = ROOT / 'tests/programs/insert-locations'
        source = fixtures / 'main.b'
        for variant, location in (('1', expected_text('insert-locations.stderr')), ('2', expected_text('insert-locations_2.stderr'))):
            with self.subTest(variant=variant):
                header = fixtures / variant / 'I_BROKEN'
                run = subprocess.run([CLI, '-I', header.parent, source, '-o', self.c],
                                     text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(header) + location, run.stderr)
        header = fixtures / '3' / 'I_BROKEN'
        run = self.run_native(fixtures / 'main-variant-2.b', options=('-I', header.parent))
        self.assertIn(expected_text('insert-locations_3.stderr', header=header).encode(), run.stderr)

    def test_bang_subroutine_names(self):
        main = ROOT / 'tests/routines/bang-subroutine-names/main.b'
        plain = ROOT / 'tests/routines/bang-subroutine-names/plain.b'
        bang = ROOT / 'tests/routines/bang-subroutine-names/bang.b'
        run = self.run_native(main, plain, bang)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('bang-subroutine-names.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_call_aliases_and_expression_arguments(self):
        caller = ROOT / 'tests/routines/call-aliases-and-expression-arguments/caller.b'
        callee = ROOT / 'tests/routines/call-aliases-and-expression-arguments/callee.b'
        run = self.run_native(callee, caller)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('call-aliases-and-expression-arguments.stdout'))

    def test_indirect_call(self):
        main = ROOT / 'tests/routines/indirect-call/main.b'
        work = ROOT / 'tests/routines/indirect-call/work.b'
        switch = ROOT / 'tests/routines/indirect-call/switch.b'
        done = ROOT / 'tests/routines/indirect-call/done.b'
        run = self.run_native(main, work, switch, done)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('indirect-call.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_empty_actual_uses_local_storage_for_mat_formal(self):
        main = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/main.b'
        load = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/load.b'
        scalar = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/scalar.b'
        result = self.run_native(main, load, scalar)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('empty-actual-uses-local-storage-for-mat-formal.stdout'), b''))

    def test_empty_mat_actual_requires_dimension_before_use(self):
        main = ROOT / 'tests/routines/empty-mat-actual-requires-dimension-before-use/main.b'
        load = ROOT / 'tests/routines/empty-mat-actual-requires-dimension-before-use/load.b'
        result = self.run_native(main, load)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (1, b'', expected_text('empty-mat-actual-requires-dimension-before-use.stderr', load=load).encode()))

    def test_callc_subroutine_exists_checks_linked_subroutines(self):
        main = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main.b'
        subroutine = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/worker.b'
        function = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/compute.b'
        result = self.run_native(main, subroutine, function)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('callc-subroutine-exists-checks-linked-subroutines.stdout'), b''))

        main = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main-variant-2.b'
        result = self.run_native(main)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('callc-subroutine-exists-checks-linked-subroutines_2.stdout'), b''))

    def test_callc_subroutine_exists_requires_two_arguments(self):
        for case_number, (arguments, marker, message) in enumerate((
            ("'WORKER'", ')', expected_text('callc-subroutine-exists-requires-two-arguments.stderr')),
            ("'WORKER', Info, 0", ', 0', expected_text('callc-subroutine-exists-requires-two-arguments_2.stderr')),
        ), 1):
            with self.subTest(arguments=arguments):
                statement = f'CRT CALLC JBASESubroutineExist({arguments})'
                source = ROOT / 'tests/routines/callc-subroutine-exists-requires-two-arguments' / f'main_{case_number}.b'
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('callc-subroutine-exists-requires-two-arguments_3.stderr', source=source, value_2=statement.rindex(marker) + 1, message=message), result.stderr)

    def test_call_expands_equates_in_arguments_and_indirect_targets(self):
        main = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/main.b'
        direct = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/direct.b'
        prefixed = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/prefixed.b'
        run = self.run_native(main, direct, prefixed)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('call-expands-equates-in-arguments-and-indirect-targets.stdout'), b''))

    def test_lit_equates_expand_quoted_source(self):
        main = ROOT / 'tests/programs/lit-equates-expand-quoted-source/main.b'
        show = ROOT / 'tests/programs/lit-equates-expand-quoted-source/show.b'
        run = self.run_native(main, show)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (0, expected_bytes('lit-equates-expand-quoted-source.stdout'), b''))

    def test_lit_equate_diagnostic_points_inside_definition(self):
        definition = 'EQUATE BROKEN LIT "CRT MISSING"'
        include = ROOT / 'tests/programs/lit-equate-diagnostic-points-inside-definition/I_INVALID'
        source = ROOT / 'tests/programs/lit-equate-diagnostic-points-inside-definition/main.b'
        result = subprocess.run([str(ROOT / 'jbcc'), str(source), '-o', str(self.work / 'main.c')],
                                capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('lit-equate-diagnostic-points-inside-definition.stderr', include=include, value_2=definition.index('MISSING') + 1).encode(),
                      result.stderr)

    def test_preprocessor_conditionals_and_include_guards(self):
        source = ROOT / 'tests/programs/preprocessor-conditionals-and-include-guards/guarded.b'
        result = self.run_native(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('preprocessor-conditionals-and-include-guards.stdout'), b''))

    def test_defc_declarations_and_runtime_diagnostics(self):
        for fixture_name, diagnostic in (
            ('foreign_1.b', b''),
            ('foreign_2.b', expected_bytes('defc-declarations-and-runtime-diagnostics.stderr')),
            ('foreign_3.b', expected_bytes('defc-declarations-and-runtime-diagnostics_2.stderr')),
            ('foreign_4.b', expected_bytes('defc-declarations-and-runtime-diagnostics_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/defc-declarations-and-runtime-diagnostics' / fixture_name
                result = self.run_native(source)
                if diagnostic:
                    self.assertEqual((result.returncode, result.stdout), (1, b''))
                    self.assertEqual(result.stderr, os.fsencode(source) + diagnostic + b'\n')
                else:
                    self.assertEqual((result.returncode, result.stdout, result.stderr),
                                     (0, expected_bytes('defc-declarations-and-runtime-diagnostics.stdout'), b''))

    def test_defc_rejects_invalid_types_and_argument_counts(self):
        for fixture_name, diagnostic in (
            ('foreign_1.b', expected_text('defc-rejects-invalid-types-and-argument-counts.stderr')),
            ('foreign_2.b', expected_text('defc-rejects-invalid-types-and-argument-counts_2.stderr')),
            ('foreign_3.b', expected_text('defc-rejects-invalid-types-and-argument-counts_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/defc-rejects-invalid-types-and-argument-counts' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, f"{source}{diagnostic}\n")

    def test_preprocessor_conditional_diagnostics(self):
        fixtures = ROOT / 'tests/programs/preprocessor-conditional-diagnostics'
        source = fixtures / 'main.b'
        for variant, location in (
            ('1', expected_text('preprocessor-conditional-diagnostics.stderr')),
            ('2', expected_text('preprocessor-conditional-diagnostics_2.stderr')),
            ('3', expected_text('preprocessor-conditional-diagnostics_3.stderr')),
            ('4', expected_text('preprocessor-conditional-diagnostics_4.stderr')),
            ('5', expected_text('preprocessor-conditional-diagnostics_5.stderr')),
        ):
            with self.subTest(variant=variant):
                include = fixtures / variant / 'I_BAD'
                result = subprocess.run([CLI, '-I', include.parent, source, '-o', self.c],
                                        text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(include) + location, result.stderr)

    def test_quoted_and_punctuated_direct_routine_names(self):
        main = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/main.b'
        star = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/star.b'
        dashed = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/dashed.b'
        quoted_header = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/quoted.b'
        result = self.run_native(main, star, dashed, quoted_header)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('quoted-and-punctuated-direct-routine-names.stdout'), b''))

    def test_quoted_direct_target_preserves_whitespace_and_punctuation(self):
        main = ROOT / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main.b'
        result = subprocess.run([CLI, main, '-o', self.c], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('quoted-direct-target-preserves-whitespace-and-punctuation.stderr', main=main))

        main = ROOT / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main-variant-2.b'
        result = subprocess.run([CLI, main, '-o', self.c], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('quoted-direct-target-preserves-whitespace-and-punctuation_2.stderr', main=main))

    def test_indirect_call_diagnostics(self):
        fixtures = ROOT / 'tests/routines/indirect-call-diagnostics'
        sub = fixtures / 'update.b'
        for fixture_name, name, units, message in (
                ('main_1.b', 'MISSING', (), expected_text('indirect-call-diagnostics.stderr')),
                ('main_2.b', 'update', (sub,), expected_text('indirect-call-diagnostics.stderr')),
                ('main_3.b', 'UPDATE', (sub,), expected_text('indirect-call-diagnostics_2.stderr')),
                ('main_4.b', 'UPDATE', (sub,), expected_text('indirect-call-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                main = fixtures / fixture_name
                run = self.run_native(main, *units)
                self.assertNotEqual(run.returncode, 0)
                self.assertEqual(run.stdout, b'')
                self.assertIn(expected_text('indirect-call-diagnostics_3.stderr', main=main, message=message, value_3=name).encode(), run.stderr)

    def test_indirect_call_through_matrix_element(self):
        main = ROOT / 'tests/routines/indirect-call-through-matrix-element/main.b'
        add = ROOT / 'tests/routines/indirect-call-through-matrix-element/add.b'
        report = ROOT / 'tests/routines/indirect-call-through-matrix-element/report.b'
        change = ROOT / 'tests/routines/indirect-call-through-matrix-element/change.b'
        result = self.run_native(main, add, report, change)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('indirect-call-through-matrix-element.stdout'), b''))

    def test_indirect_matrix_call_uses_normal_matrix_diagnostics(self):
        for fixture_name, message in (
            ('main_1.b', expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics.stderr')),
            ('main_2.b', expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/indirect-matrix-call-uses-normal-matrix-diagnostics' / fixture_name
                result = self.run_native(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr, expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics_3.stderr', source=source, message=message).encode())

    def test_multiline_call(self):
        caller = ROOT / 'tests/routines/multiline-call/caller.b'
        callee = ROOT / 'tests/routines/multiline-call/callee.b'
        run = self.run_native(caller, callee)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('multiline-call.stdout'))

    def test_external_function(self):
        directory = ROOT / 'tests/routines'
        binary = self.work / 'program'
        subprocess.run([CLI, '--exe', directory / 'function.caller.b',
                        directory / 'DOUBLE.IT', '-o', binary], check=True)
        self.assertEqual(subprocess.check_output([binary]), expected_bytes('external-function.stdout'))

    def test_deffun_call_as_statement_discards_return_and_updates_argument(self):
        main = ROOT / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/main.b'
        function = ROOT / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/function.b'
        result = self.run_native(main, function)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('deffun-call-as-statement-discards-return-and-updates-argument.stdout'), b''))

    def test_function_arguments_and_returns(self):
        main = ROOT / 'tests/routines/function-arguments-and-returns/main.b'
        inc = ROOT / 'tests/routines/function-arguments-and-returns/INC'
        empty = ROOT / 'tests/routines/function-arguments-and-returns/EMPTY'
        run = self.run_native(empty, inc, main)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('function-arguments-and-returns.stdout'))

    def test_matrix_parameters(self):
        main = ROOT / 'tests/routines/matrix-parameters/main.b'
        sub = ROOT / 'tests/routines/matrix-parameters/relay.b'
        func = ROOT / 'tests/routines/matrix-parameters/edit.b'
        run = self.run_native(main, sub, func)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('matrix-parameters.stdout'))

    def test_matrix_parameter_diagnostics(self):
        for case_number, (call, formal) in enumerate([('CALL S(MAT A)', 'X'), ('CALL S(N)', 'MAT X')], 1):
            main = ROOT / 'tests/routines/matrix-parameter-diagnostics' / f'main_{case_number}.b'
            sub = ROOT / 'tests/routines/matrix-parameter-diagnostics' / f'sub_{case_number}.b'
            result = subprocess.run([CLI, main, sub, '-o', self.c], text=True, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(expected_text('matrix-parameter-diagnostics.stderr', main=main), result.stderr)
        main = ROOT / 'tests/routines/matrix-parameter-diagnostics/main-variant-2.b'
        for fixture_name, message in (
            ('sub-variant-2_1.b', expected_text('matrix-parameter-diagnostics_3.stderr')),
            ('sub-variant-2_2.b', expected_text('matrix-parameter-diagnostics_4.stderr')),
            ('sub-variant-2_3.b', expected_text('matrix-parameter-diagnostics_5.stderr')),
        ):
            sub = ROOT / 'tests/routines/matrix-parameter-diagnostics' / fixture_name
            run = self.run_native(main, sub)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('matrix-parameter-diagnostics_2.stderr', sub=sub).encode(), run.stderr)
            self.assertIn(message.encode(), run.stderr)

    def test_function_diagnostics(self):
        definition = ROOT / 'tests/routines/DOUBLE.IT'
        for fixture_name, message in (
            ('main_1.b', expected_text('function-diagnostics.stderr')),
            ('main_2.b', expected_text('function-diagnostics_2.stderr')),
            ('main_3.b', expected_text('function-diagnostics_3.stderr')),
            ('main_4.b', expected_text('function-diagnostics_4.stderr')),
        ):
            with self.subTest(source=fixture_name):
                main = ROOT / 'tests/routines/function-diagnostics' / fixture_name
                run = subprocess.run([CLI, main, definition, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(str(main) + message, run.stderr)

    def test_indexed_jump_selector(self):
        function = ROOT / 'tests/programs/indexed-jump-selector/pick.b'
        source = ROOT / 'tests/programs/indexed-jump-selector/dispatch.b'
        run = self.run_native(source, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('indexed-jump-selector.stdout'))
        for fixture_name in (
            'dispatch-variant-2_1.b',
            'dispatch-variant-2_2.b',
        ):
            source = ROOT / 'tests/programs/indexed-jump-selector' / fixture_name
            run = self.run_native(source)
            self.assertNotEqual(run.returncode, 0)
            self.assertIn(expected_text('indexed-jump-selector.stderr', source=source).encode(), run.stderr)

    def test_indexed_jump_range(self):
        source = ROOT / 'tests/programs/indexed-jump-range.b'
        run = self.run_native(source)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, expected_bytes('indexed-jump-range.stdout'))
        expected = [f'{source}:{line}:1: warning: ON selector out of range, using label {line}'
                    for line in (1, 2)]
        self.assertEqual(run.stderr.decode().splitlines(), expected)
        binary = self.work / 'pick'
        env = dict(os.environ, CC_FLAGS='-DJBCC_ON_FALLTHROUGH')
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True, env=env)
        run = subprocess.run([binary], capture_output=True)
        self.assertEqual(run.returncode, 0)
        self.assertEqual(run.stdout, expected_bytes('indexed-jump-range_2.stdout'))
        self.assertEqual(run.stderr, b'')

    def test_jump_discards_step_when_reentering_a_completed_for(self):
        source = ROOT / 'tests/programs/jump-discards-step-when-reentering-a-completed-for.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, expected_bytes('jump-discards-step-when-reentering-a-completed-for.stdout'))
        self.assertEqual(result.stderr, expected_text('jump-discards-step-when-reentering-a-completed-for.stderr', source=source).encode())

    def test_next_after_jump_requires_assigned_counter(self):
        source = ROOT / 'tests/programs/next-after-jump-requires-assigned-counter.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, expected_bytes('next-after-jump-requires-assigned-counter.stdout'))
        self.assertEqual(result.stderr, expected_text('next-after-jump-requires-assigned-counter.stderr', source=source).encode())

    def test_return_to_unwinds_subroutine(self):
        main = ROOT / 'tests/programs/return-to-unwinds-subroutine/main.b'
        sub = ROOT / 'tests/programs/return-to-unwinds-subroutine/sub.b'
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('return-to-unwinds-subroutine.stdout'))

    def test_return_to_without_caller(self):
        main = ROOT / 'tests/programs/return-to-without-caller.b'
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('return-to-without-caller.stderr', main=main).encode(), run.stderr)

    def test_return_to_bypasses_for_header_with_explicit_step(self):
        main = ROOT / 'tests/programs/return-to-bypasses-for-header-with-explicit-step.b'
        run = self.run_native(main)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (1, expected_bytes('return-to-bypasses-for-header-with-explicit-step.stdout'), expected_text('return-to-bypasses-for-header-with-explicit-step.stderr', main=main).encode()))

    def test_bad_routine_references(self):
        sub = ROOT / 'tests/routines/bad-routine-references/sub.b'
        for fixture_name, message in (
            ('main_1.b', expected_text('bad-routine-references.stderr')),
            ('main_2.b', expected_text('bad-routine-references_2.stderr')),
            ('main_3.b', expected_text('bad-routine-references_3.stderr')),
            ('main_4.b', expected_text('bad-routine-references_4.stderr')),
            ('main_5.b', expected_text('bad-routine-references_5.stderr')),
            ('main_6.b', expected_text('bad-routine-references_6.stderr')),
            ('main_7.b', expected_text('bad-routine-references_7.stderr')),
            ('main_8.b', expected_text('bad-routine-references_8.stderr')),
            ('main_9.b', expected_text('bad-routine-references_9.stderr')),
            ('main_10.b', expected_text('bad-routine-references_10.stderr')),
            ('main_11.b', expected_text('bad-routine-references_11.stderr')),
            ('main_12.b', expected_text('bad-routine-references_12.stderr')),
            ('main_13.b', expected_text('bad-routine-references_13.stderr')),
            ('main_14.b', expected_text('bad-routine-references_9.stderr')),
            ('main_15.b', expected_text('bad-routine-references_14.stderr')),
            ('main_16.b', expected_text('bad-routine-references_5.stderr')),
            ('main_17.b', expected_text('bad-routine-references_15.stderr')),
            ('main_18.b', expected_text('bad-routine-references_16.stderr')),
        ):
            with self.subTest(source=fixture_name):
                main = ROOT / 'tests/routines/bad-routine-references' / fixture_name
                run = subprocess.run([CLI, main, sub, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message, run.stderr)

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

    def test_deferred_scalar_read_warns_and_fails_only_when_reached(self):
        source = ROOT / 'tests/programs/deferred-scalar-read-warns-and-fails-only-when-reached.b'
        binary = self.work / 'program'
        command = [CLI, '--exe', source, '-o', binary]
        strict = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual(strict.returncode, 1)
        self.assertEqual(strict.stderr, expected_text('deferred-scalar-read-warns-and-fails-only-when-reached.stderr', source=source))
        deferred = subprocess.run([*command, '--defer-unassigned-reads'], capture_output=True, text=True, check=True)
        self.assertEqual(deferred.stderr,
                         expected_text('deferred-scalar-read-warns-and-fails-only-when-reached_2.stderr', source=source))
        for flag, expected in (
            ('0', (0, expected_bytes('deferred-scalar-read-warns-and-fails-only-when-reached.stdout'), b'')),
            ('1', (1, b'', expected_text('deferred-scalar-read-warns-and-fails-only-when-reached_3.stderr', source=source).encode())),
        ):
            with self.subTest(flag=flag):
                run = subprocess.run([binary], capture_output=True, timeout=5,
                                     env=dict(os.environ, JBCC_TEST_DEFERRED_READ=flag))
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_deferred_compound_assignment_checks_previous_value_when_reached(self):
        source = ROOT / 'tests/programs/deferred-compound-assignment.b'
        binary = self.work / 'program'
        command = [CLI, '--exe', source, '-o', binary]
        strict = subprocess.run(command, capture_output=True, text=True)
        self.assertEqual((strict.returncode, strict.stderr),
                         (1, expected_text('deferred-compound-assignment-checks-previous-value-when-reached.stderr', source=source)))
        deferred = subprocess.run([*command, '--defer-unassigned-reads'], capture_output=True, text=True, check=True)
        self.assertEqual(deferred.stderr.splitlines(), [
            expected_text('deferred-compound-assignment-checks-previous-value-when-reached_2.stderr', source=source),
            expected_text('deferred-compound-assignment-checks-previous-value-when-reached_3.stderr', source=source),
        ])
        for mode, expected in (
            ('skip', (0, expected_bytes('deferred-compound-assignment-checks-previous-value-when-reached.stdout'), b'')),
            ('add', (1, b'', expected_text('deferred-compound-assignment-checks-previous-value-when-reached.stderr', source=source).encode())),
            ('append', (1, b'', expected_text('deferred-compound-assignment-checks-previous-value-when-reached_4.stderr', source=source).encode())),
        ):
            with self.subTest(mode=mode):
                run = subprocess.run([binary, mode], capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_deferred_reads_still_reject_unknown_functions(self):
        source = ROOT / 'tests/programs/deferred-reads-still-reject-unknown-functions.b'
        result = subprocess.run([CLI, '--defer-unassigned-reads', source, '-o', self.c],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('deferred-reads-still-reject-unknown-functions.stderr', source=source))

    def test_corpus_reports_deferred_reads_in_includes(self):
        corpus = ROOT / 'tests/corpus/deferred-include-reads'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', corpus]
        strict = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(strict['files']['main.b'], {
            'status': 'rejected',
            'diagnostic': "I_EXAMPLE:2:5: unknown variable or unsupported function 'Missing'",
        })
        deferred = json.loads(subprocess.check_output(command + ['--defer-unassigned-reads'], text=True))
        self.assertEqual(deferred['first_blockers'], {})
        self.assertEqual(deferred['files']['main.b'], {
            'status': 'translated',
            'warnings': ["I_EXAMPLE:2:5: warning: read of 'Missing' before assignment is deferred to runtime"],
        })

    def test_corpus_t24_fixes_apply_in_memory_to_known_files(self):
        cases = {
            'STEST.AZ.PD.DATES.CHK': (
                b"EQUATE AZ.SLS.TYPE.I TO 2\r\nA = 'a':@FM:'b'\r\nB = A<.AZ.SLS.TYPE.I,1>\r\nCRT B\r\n",
                [(3, 7, '.AZ.SLS.TYPE.I', 'AZ.SLS.TYPE.I')],
            ),
            'TK.VALIDATE.SYSGEN.FILES': (
                b'* 1ST.RECORD = 1\n1ST.RECORD = 1\nIF 1ST.RECORD THEN CRT "1ST.RECORD"\n',
                [(2, 1, '1ST.RECORD', 'FIRST.RECORD'), (3, 4, '1ST.RECORD', 'FIRST.RECORD')],
            ),
            'LIST.DATA': (
                b'THE.ARGS = "F...":FM:"F..."\nCRT THE.ARGS\n',
                [(1, 19, 'FM', '@FM')],
            ),
        }
        for name, (source, _) in cases.items():
            (self.work / name).write_bytes(source)
        (self.work / 'nested').mkdir()
        (self.work / 'nested/LIST.DATA').write_bytes(cases['LIST.DATA'][0])

        command = [sys.executable, ROOT / 'tools/check_corpus.py', self.work]
        strict = json.loads(subprocess.check_output(command, text=True))
        reports = json.loads(subprocess.check_output(command + ['--t24-source-fixes'], text=True))['files']
        for name, (source, edits) in cases.items():
            with self.subTest(name=name):
                self.assertEqual(strict['files'][name]['status'], 'rejected')
                self.assertEqual(reports[name], {
                    'status': 'translated',
                    'source_fixes': [
                        dict(file=name, line=line, column=column, before=before, after=after)
                        for line, column, before, after in edits
                    ],
                })
                self.assertEqual((self.work / name).read_bytes(), source)
        self.assertEqual(reports['nested/LIST.DATA'], strict['files']['nested/LIST.DATA'])

    def test_r07_corpus_can_apply_source_fixes_and_report_include_stub(self):
        fixture = ROOT / 'tests/corpus/r07'
        root = fixture / '200707-R07'
        bp = root / 'GLOBUS.BP'
        original = {path: path.read_bytes() for path in bp.iterdir()}
        command = [sys.executable, ROOT / 'tools/check_corpus.py', root]
        baseline = json.loads(subprocess.check_output(command, text=True))['files']
        missing = 'GLOBUS.BP/LA.FIXTURE.b'
        compare = 'GLOBUS.BP/COMPARE.DB.JBASE'
        dates = 'GLOBUS.BP/STEST.AZ.PD.DATES.CHK'
        rates = 'GLOBUS.BP/MG.EOD.REDEFINE.CONTRACT.RATES'
        cdf = 'GLOBUS.BP/TU.LIB.STD.CDF'
        inv = 'GLOBUS.BP/TU.LIB.STD.INV'
        self.assertIn("include file 'I_F.LA.PARAMETER' not found", baseline[missing]['diagnostic'])
        self.assertEqual(baseline[dates]['status'], 'rejected')
        self.assertEqual(baseline[rates], {
            'status': 'rejected',
            'diagnostic': f"{rates}:5:14: expected 1 subscripts for 'CR.REC'",
        })
        self.assertEqual(baseline[cdf]['status'], 'rejected')
        self.assertEqual(baseline[inv]['status'], 'rejected')

        options = ['--t24-source-fixes', '--stub-r07-la-parameter']
        report = json.loads(subprocess.check_output(command + options, text=True))['files']
        self.assertEqual(report[missing], {'status': 'translated', 'include_stubs': ['I_F.LA.PARAMETER']})
        self.assertEqual(report[compare], {
            'status': 'translated',
            'source_fixes': [dict(file=compare, line=1, column=10,
                                  before='/usr/jbc/include/JBC.h', after='JBC.h')],
        })
        self.assertEqual(report[dates], {
            'status': 'translated',
            'source_fixes': [dict(file=dates, line=3, column=16,
                                  before='.AZ.SLS.TYPE.I', after='AZ.SLS.TYPE.I')],
        })
        self.assertEqual(report[rates], {
            'status': 'translated',
            'source_fixes': [dict(file=rates, line=5, column=34, before=',1', after='')],
        })
        self.assertEqual(report[cdf], {
            'status': 'translated',
            'source_fixes': [
                dict(file=cdf, line=1, column=6, before='-3.125e-002', after='-0.03125'),
                dict(file=cdf, line=2, column=6, before='1.25E2', after='125'),
            ],
        })
        self.assertEqual(report[inv], {
            'status': 'translated',
            'source_fixes': [dict(file=inv, line=1, column=6, before='1.2300E+02', after='123.00')],
        })

        with_real_include = command + options + ['-I', fixture / 'real-includes']
        report = json.loads(subprocess.check_output(with_real_include, text=True))['files']
        self.assertEqual(report[missing], {'status': 'translated'})
        self.assertEqual({path: path.read_bytes() for path in bp.iterdir()}, original)

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

    def test_corpus_can_summarize_next_name_mismatch_warnings(self):
        corpus = ROOT / 'tests/corpus/next-name-warnings'
        good = corpus / 'good.b'
        bad = corpus / 'bad.b'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', corpus, '-j', '2']
        verbose = subprocess.run(command, capture_output=True, text=True, check=True)
        quiet = subprocess.run(command + ['--quiet-next-warnings'], capture_output=True, text=True, check=True)
        report = json.loads(quiet.stdout)
        self.assertEqual(report, json.loads(verbose.stdout))
        self.assertEqual(report['files']['good.b']['status'], 'translated')
        self.assertEqual(report['files']['bad.b']['status'], 'rejected')
        for source in (good, bad):
            self.assertIn(expected_text('corpus-can-summarize-next-name-mismatch-warnings.stderr', source=source), verbose.stderr)
        self.assertEqual(quiet.stderr.splitlines(), [
            expected_text('corpus-can-summarize-next-name-mismatch-warnings_2.stderr', good=good),
            expected_text('corpus-can-summarize-next-name-mismatch-warnings_3.stderr'),
        ])

    def test_corpus_api_coverage_counts_parsed_calls_by_form(self):
        fixture = ROOT / 'tests/corpus/api-coverage'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', fixture / 'corpus',
                   '--api-catalogue', fixture / 'spec']
        report = json.loads(subprocess.check_output(command, text=True))
        entries = {(api['kind'], api['name']): api for api in report['api_coverage']['apis']}
        self.assertEqual(entries['expression', 'ABS']['guide'], 'https://jbc-lang.org/pages/abs.html')
        self.assertEqual(entries['expression', 'ABS']['nominal_arity'], 1)
        self.assertFalse(any(form['occurrences'] for form in entries['expression', 'ABS']['forms']))
        self.assertEqual(entries['defc', 'Unused']['forms'], [])
        bitor, = entries['expression', 'BITOR']['forms']
        expected = {'arity': 2, 'occurrences': 4, 'units': 3, 'c99_checked_units': 2}
        self.assertEqual({k: bitor[k] for k in expected}, expected)
        self.assertEqual(bitor['example'], {'unit': 'main.b', 'file': 'I_EXAMPLE', 'line': 1, 'column': 16})
        native, = entries['defc', 'CExample']['forms']
        self.assertEqual((native['occurrences'], native['jbcc_support']), (1, 'backend required'))
        forms = {form['variant']: form['jbcc_support'] for form in entries['expression', 'ENCRYPT']['forms']}
        self.assertEqual(forms, {'method 1 (ROT13)': 'ROT13 implemented', 'method 4 (Base64)': 'backend required'})
        report_path = self.work / 'coverage.json'
        report_path.write_text(json.dumps(report))
        markdown = subprocess.check_output([sys.executable, ROOT / 'tools/api_coverage.py', report_path], text=True)
        self.assertIn(expected_text('corpus-api-coverage-counts-parsed-calls-by-form.stdout'), markdown)
        self.assertIn(expected_text('corpus-api-coverage-counts-parsed-calls-by-form_2.stdout'), markdown)

    def test_corpus_uses_t24_catalog_kinds_for_selected_extract(self):
        fixture = ROOT / 'tests/corpus/file-catalog'
        catalog = self.work / 'catalog.sqlite'
        with sqlite3.connect(catalog) as db:
            db.executescript((fixture / 'catalog.sql').read_text())
        root = fixture / 'sample-r07'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', root, '--t24-catalog', catalog]
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['counts'], {'C header': 1, 'include fragment': 1, 'translated': 2})
        self.assertEqual(report['files']['GLOBUS.BP/Constants.h']['status'], 'include fragment')
        self.assertEqual(report['files']['GLOBUS.BP/Native.h']['status'], 'C header')
        self.assertEqual(report['files']['GLOBUS.BP/I_Unit']['status'], 'translated')
        self.assertEqual(report['files']['GLOBUS.BP/Main.b']['status'], 'translated')

    def test_corpus_index_resolves_and_reports_component_includes(self):
        fixture = ROOT / 'tests/corpus/indexed-includes'
        catalog = self.work / 'catalog.sqlite'
        with sqlite3.connect(catalog) as db:
            db.executescript((fixture / 'catalog.sql').read_text())
        root = fixture / 'sample-r19'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', root, '--t24-catalog', catalog,
                   '--t24-indexed-includes', '--source-prefix', 'AA/Account', '-j', '2']
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['counts'], {'translated': 1, 'rejected': 2})
        self.assertEqual(report['include_lookups'], {'resolved': 3, 'missing': 1, 'ambiguous': 1})
        files = report['files']
        main = 'AA/Account/Private/Main.b'
        self.assertEqual(files[main]['package_directives'], [
            dict(kind='package', name='AA.Account', file=main, line=1, column=10),
            dict(kind='using', name='BB.Billing', file=main, line=2, column=8),
        ])
        traces = files[main]['include_lookups']
        self.assertEqual([(e['file'], e['rule'], e['resolved']) for e in traces], [
            (main, 'source directory', 'AA/Account/Private/I_Local'),
            (main, 'component', 'AA/Account/Public/I_Choice'),
            ('AA/Account/Public/I_Choice', 'release index', 'BB/Billing/Public/I_Global'),
        ])
        ambiguous = files['AA/Account/Private/Ambiguous.b']['include_lookups'][0]
        self.assertEqual(ambiguous['status'], 'ambiguous')
        self.assertEqual(ambiguous['candidates'], ['BB/Billing/Public/I_Tied', 'Flat/I_Tied'])
        missing = files['AA/Account/Private/Missing.b']
        self.assertEqual(missing['include_lookups'][0]['status'], 'missing')
        self.assertEqual(missing['package_directives'][0]['name'], 'AA.Account')

    def test_corpus_checks_qualified_component_signatures(self):
        fixture = ROOT / 'tests/corpus/component-calls'
        catalog = self.work / 'catalog.sqlite'
        with sqlite3.connect(catalog) as db:
            db.executescript((fixture / 'catalog.sql').read_text())
        command = [sys.executable, ROOT / 'tools/check_corpus.py', fixture / 'sample-r19',
                   '--t24-catalog', catalog, '--t24-component-calls', '-j', '2']
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['counts'], {'translated': 1, 'rejected': 8})
        self.assertTrue(report['selection']['component_calls'])
        self.assertEqual(report['files']['Main.b']['status'], 'translated')
        failures = {
            'WrongArity.b': "2:5: arguments disagree with component declaration for 'Shop.Prices.getCurrent'",
            'WrongKind.b': "2:5: arguments disagree with component declaration for 'Shop.Prices.Format'",
            'PrivateAccess.b': "2:1: component member 'Shop.Prices.Reset' has private access",
            'ModuleAccess.b': "2:1: component member 'Shop.Prices.Clear' has module access",
            'MissingSharedMember.b': "2:1: unsupported statement 'Shop.Shared.setOnlyHere'",
            'PrivateTableAccess.b': "2:5: component member 'Shop.Prices.Ledger.Read' has private access",
            'WrongTableArity.b': "2:1: arguments disagree with component declaration for 'Shop.Prices.Prices.Write'",
            'VoidExpression.b': "2:5: component method 'Shop.Prices.setCurrent' has no return value",
        }
        for name, diagnostic in failures.items():
            self.assertEqual(report['files'][name]['diagnostic'], f'{name}:{diagnostic}')

    def test_duplicate_package_reports_its_source_location(self):
        source = ROOT / 'tests/programs/duplicate-package.b'
        run = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual((run.returncode, run.stderr), (1, expected_text('duplicate-package-reports-its-source-location.stderr', source=source)))

    def test_multi_unit_program_requires_package_aware_linkage(self):
        main = ROOT / 'tests/snippets/package-directives.b'
        routine = ROOT / 'tests/routines/show-parasentence.b'
        run = subprocess.run([CLI, main, routine, '-o', self.c], capture_output=True, text=True)
        self.assertEqual((run.returncode, run.stderr), (1, expected_text('multi-unit-program-requires-package-aware-linkage.stderr', main=main)))

    def test_source_encoding_preserves_legacy_and_utf8_literal_bytes(self):
        source = ROOT / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/main.b'
        routine = ROOT / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/show.b'
        result = self.run_native(source, routine, options=('--source-encoding', 'bytes'))
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('source-encoding-preserves-legacy-and-utf8-literal-bytes.stdout'), b''))

    def test_source_nul_is_ignored_in_comments(self):
        source = ROOT / 'tests/programs/source-nul-is-ignored-in-comments/main.b'
        result = self.run_native(source)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('source-nul-is-ignored-in-comments.stdout'), b''))

    def test_source_nul_reports_its_location_in_active_text(self):
        fixtures = ROOT / 'tests/programs/source-nul-reports-its-location-in-active-text'
        source = fixtures / 'main.b'
        for variant, column in (('1', 10), ('2', 12), ('3', 11), ('4', 17)):
            with self.subTest(variant=variant):
                include = fixtures / variant / 'I_VALUE'
                result = subprocess.run([CLI, '-I', include.parent, source, '-o', self.c],
                                        text=True, capture_output=True)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stderr, expected_text('source-nul-reports-its-location-in-active-text.stderr', include=include, column=column))

    def test_default_source_encoding_reports_invalid_utf8_in_an_include(self):
        source = ROOT / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/main.b'
        prefix = "* étoile "
        include = ROOT / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/I_SHARED'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('default-source-encoding-reports-invalid-utf8-in-an-include.stderr', include=include, value_2=len(prefix) + 1))
        self.assertFalse(self.c.exists())

    def test_corpus_report_can_preserve_source_bytes(self):
        corpus = ROOT / 'tests/corpus/legacy-include-bytes'
        command = [sys.executable, ROOT / 'tools/check_corpus.py', corpus]
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['counts'], {'encoding': 1, 'include fragment': 1})
        self.assertEqual(report['files']['main.b'],
                         {'status': 'encoding', 'diagnostic': 'I_SHARED:1:10: invalid UTF-8 at byte 0xfd'})
        report = json.loads(subprocess.check_output(command + ['--source-encoding', 'bytes'], text=True))
        self.assertEqual(report['counts'], {'translated': 1, 'include fragment': 1})

    def test_corpus_matrix_signatures(self):
        (self.work / 'forward').write_text('SUBROUTINE F(MAT A)\nCALL EXT(MAT A)\n'
                                          'IF 0 THEN CALL F(MAT A)\n')
        (self.work / 'mixed').write_text('DIM A(1)\nCALL EXT(MAT A)\nCALL EXT(A(1))\n')
        result = subprocess.run([sys.executable, ROOT / 'tools/check_corpus.py', self.work],
                                capture_output=True, text=True, check=True)
        files = json.loads(result.stdout)['files']
        self.assertEqual(files['forward']['status'], 'translated')
        self.assertIn('mixed:3:6: external calls disagree on signature', files['mixed']['diagnostic'])

    def test_corpus_checks_external_arities_and_reports_the_linkage_conflict(self):
        source = self.work / 'caller'
        source.write_text("CALL Report('')\nCALL Report\n")
        command = [sys.executable, ROOT / 'tools/check_corpus.py', self.work]
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['first_blockers'], {})
        self.assertEqual(report['files']['caller'], {
            'status': 'translated',
            'linkage_diagnostic': "caller:2:6: calls to 'Report' use different argument counts (1 and 0)",
        })

        definition = self.work / 'report'
        definition.write_text('SUBROUTINE Report(Value)\nCRT Value\n')
        result = subprocess.run([CLI, source, definition, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('corpus-checks-external-arities-and-reports-the-linkage-conflict.stderr', source=source))

        source.write_text('SUBROUTINE Recur(MAT A)\nCALL Recur\n')
        report = json.loads(subprocess.check_output(command, text=True))
        self.assertEqual(report['files']['caller'], {
            'status': 'rejected',
            'diagnostic': 'caller:2:6: recursive call has incompatible signature',
        })

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
        expected = (expected_bytes('ascii-and-ebcdic.stdout') + data.decode('cp037').encode('latin-1')
                    + data.decode('latin-1').encode('cp037') + data + data + expected_bytes('ascii-and-ebcdic_2.stdout'))
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, b''))

    def test_ascii_and_ebcdic_argument_counts(self):
        for fixture_name, name in (
            ('invalid_1.b', 'ASCII'),
            ('invalid_2.b', 'EBCDIC'),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/ascii-and-ebcdic-argument-counts' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('ascii-and-ebcdic-argument-counts.stderr', source=source, value_2=name), result.stderr)

    def test_utf8_and_latin1_round_trip_all_nonzero_bytes(self):
        data = bytes(range(1, 256))
        (self.work / 'input').write_bytes(data)
        source = ROOT / 'tests/programs/utf8-and-latin1-round-trip-all-nonzero-bytes.b'
        result = self.run_native(source, cwd=self.work)
        expected = data.decode('latin-1').encode('utf-8') + data + expected_bytes('utf8-and-latin1-round-trip-all-nonzero-bytes.stdout')
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected, b''))

    def test_latin1_rejects_malformed_and_unrepresentable_utf8(self):
        for fixture_name in (
            'encoding_1.b',
            'encoding_2.b',
            'encoding_3.b',
            'encoding_4.b',
            'encoding_5.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/latin1-rejects-malformed-and-unrepresentable-utf8' / fixture_name
                result = self.run_native(source)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr, (
                    expected_text('latin1-rejects-malformed-and-unrepresentable-utf8.stderr', source=source).encode()
                ))

    def test_seq_reads_block_bytes(self):
        (self.work / 'input').write_bytes(b'\x01\xfeAB')
        source = ROOT / 'tests/programs/seq-reads-block-bytes.b'
        result = self.run_native(source, cwd=self.work)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('seq-reads-block-bytes.stdout'), b''))

    def test_seqx_resolves_as_external_function(self):
        source = ROOT / 'tests/routines/seqx-resolves-as-external-function/main.b'
        function = ROOT / 'tests/routines/seqx-resolves-as-external-function/seqx.b'
        result = self.run_native(source, function)
        self.assertEqual((result.returncode, result.stdout, result.stderr), (0, expected_bytes('seqx-resolves-as-external-function.stdout'), b''))

    def test_seq_wrong_argument_count(self):
        source = ROOT / 'tests/programs/seq-wrong-argument-count.b'
        result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('seq-wrong-argument-count.stderr', source=source), result.stderr)

    def test_char_byte_range_diagnostics(self):
        for fixture_name, message in (
            ('char_1.b', expected_text('char-byte-range-diagnostics.stderr')),
            ('char_2.b', expected_text('char-byte-range-diagnostics_2.stderr')),
            ('char_3.b', expected_text('char-byte-range-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/char-byte-range-diagnostics' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(message.encode(), run.stderr)
                self.assertIn(expected_text('char-byte-range-diagnostics_3.stderr', source=source).encode(), run.stderr)

    def test_checksum_argument_diagnostics(self):
        for fixture_name in (
            'checksum_1.b',
            'checksum_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/checksum-argument-diagnostics' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('checksum-argument-diagnostics.stderr', source=source), result.stderr)

        source = ROOT / 'tests/programs/checksum-argument-diagnostics/checksum-variant-2.b'
        run = self.run_native(source)
        self.assertEqual((run.returncode, run.stdout, run.stderr),
                         (1, b'', expected_text('checksum-argument-diagnostics_2.stderr', source=source).encode()))

    def test_common_storage(self):
        caller = ROOT / 'tests/routines/common-storage/caller.b'
        sub = ROOT / 'tests/routines/common-storage/sub.b'
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('common-storage.stdout'))
        sub = ROOT / 'tests/routines/common-storage/sub-variant-2.b'
        result = subprocess.run([CLI, caller, sub, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('common-storage.stderr'), result.stderr)

    def test_conflicting_common_declarations(self):
        for fixture_name in (
            'conflict_1.b',
            'conflict_2.b',
            'conflict_3.b',
            'conflict_4.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/conflicting-common-declarations' / fixture_name
                run = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('conflicting-common-declarations.stderr', source=source), run.stderr)

    def test_common_member_keeps_first_slot_when_dimensioned_later(self):
        main = ROOT / 'tests/routines/common-member-keeps-first-slot-when-dimensioned-later/main.b'
        sub = ROOT / 'tests/routines/common-member-keeps-first-slot-when-dimensioned-later/update.b'
        result = self.run_native(main, sub)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('common-member-keeps-first-slot-when-dimensioned-later.stdout'), b''))

    def test_repeated_include_reuses_common_matrix_slots(self):
        main = ROOT / 'tests/routines/repeated-include-reuses-common-matrix-slots/main.b'
        sub = ROOT / 'tests/routines/repeated-include-reuses-common-matrix-slots/check.b'
        result = self.run_native(main, sub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('repeated-include-reuses-common-matrix-slots.stdout'))
        self.assertEqual(result.stderr, b'')

    def test_repeated_common_matrix_rejects_incompatible_dimensions(self):
        source = ROOT / 'tests/routines/repeated-common-matrix-rejects-incompatible-dimensions/bad.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('repeated-common-matrix-rejects-incompatible-dimensions.stderr', source=source).encode(), result.stderr)

        for fixture_name in (
            'bad-variant-2_1.b',
            'bad-variant-2_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/repeated-common-matrix-rejects-incompatible-dimensions' / fixture_name
                result = self.run_native(source)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('repeated-common-matrix-rejects-incompatible-dimensions_2.stderr', source=source).encode(), result.stderr)

    def test_dim_reuses_named_and_unnamed_common_matrix_slots(self):
        main = ROOT / 'tests/routines/dim-reuses-named-and-unnamed-common-matrix-slots/main.b'
        sub = ROOT / 'tests/routines/dim-reuses-named-and-unnamed-common-matrix-slots/update.b'
        result = self.run_native(main, sub)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('dim-reuses-named-and-unnamed-common-matrix-slots.stdout'))
        self.assertEqual(result.stderr, b'')

    def test_dim_rejects_a_common_matrix_rank_change(self):
        source = ROOT / 'tests/routines/dim-rejects-a-common-matrix-rank-change.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('dim-rejects-a-common-matrix-rank-change.stderr', source=source))

    def test_common_matrix_subscript_mismatches_report_when_reached(self):
        for fixture_name in (
            'subscripts_1.b',
            'subscripts_2.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/common-matrix-subscript-mismatches-report-when-reached' / fixture_name
                result = self.run_native(source)
                self.assertEqual((result.returncode, result.stdout), (1, expected_bytes('common-matrix-subscript-mismatches-report-when-reached.stdout')))
                self.assertEqual(result.stderr,
                                 expected_text('common-matrix-subscript-mismatches-report-when-reached.stderr', source=source).encode())

    def test_dim_reports_a_reached_common_matrix_resize(self):
        for fixture_name in (
            'shape_1.b',
            'shape_2.b',
            'shape_3.b',
            'shape_4.b',
            'shape_5.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/dim-reports-a-reached-common-matrix-resize' / fixture_name
                result = self.run_native(source)
                self.assertEqual(result.returncode, 1, result.stderr)
                self.assertEqual(result.stdout, b'')
                self.assertEqual(result.stderr, expected_text('dim-reports-a-reached-common-matrix-resize.stderr', source=source).encode())

    def test_runtime_common_dimensions(self):
        main = ROOT / 'tests/routines/runtime-common-dimensions/main.b'
        sub = ROOT / 'tests/routines/runtime-common-dimensions/change.b'
        run = self.run_native(main, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('runtime-common-dimensions.stdout'))

    def test_local_dimensions_per_invocation(self):
        main = ROOT / 'tests/routines/local-dimensions-per-invocation/main.b'
        routine = ROOT / 'tests/routines/local-dimensions-per-invocation/nested.b'
        bump = ROOT / 'tests/routines/local-dimensions-per-invocation/bump.b'
        run = self.run_native(main, routine, bump)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('local-dimensions-per-invocation.stdout'))

    def test_forward_matrix_declarations_follow_execution_order(self):
        main = ROOT / 'tests/routines/forward-matrix-declarations-follow-execution-order/main.b'
        routine = ROOT / 'tests/routines/forward-matrix-declarations-follow-execution-order/check.b'
        result = self.run_native(main, routine)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('forward-matrix-declarations-follow-execution-order.stdout'), b''))

    def test_scalar_can_be_used_before_a_later_local_dim(self):
        main = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/main.b'
        routine = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/append.b'
        result = self.run_native(main, routine)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('scalar-can-be-used-before-a-later-local-dim.stdout'), b''))

        main = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/main-variant-2.b'
        result = subprocess.run([CLI, main, '-o', self.c], text=True, capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn(expected_text('scalar-can-be-used-before-a-later-local-dim.stderr', main=main), result.stderr)

    def test_forward_matrix_errors_use_reference_location(self):
        source = ROOT / 'tests/routines/forward-matrix-errors-use-reference-location/forward.b'
        result = self.run_native(source)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('forward-matrix-errors-use-reference-location.stderr', source=source).encode())

        source = ROOT / 'tests/routines/forward-matrix-errors-use-reference-location/forward-variant-2.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('forward-matrix-errors-use-reference-location_2.stderr', source=source))

    def test_repeated_local_dim_reuses_storage_from_either_path(self):
        caller = ROOT / 'tests/routines/repeated-local-dim-reuses-storage-from-either-path/main.b'
        routine = ROOT / 'tests/routines/repeated-local-dim-reuses-storage-from-either-path/store.b'
        result = self.run_native(caller, routine)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('repeated-local-dim-reuses-storage-from-either-path.stdout'))
        self.assertEqual(result.stderr, b'')

    def test_repeated_local_dim_rejects_changed_rank(self):
        source = ROOT / 'tests/routines/repeated-local-dim-rejects-changed-rank.b'
        result = subprocess.run([CLI, source, '-o', self.c], capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stderr, expected_text('repeated-local-dim-rejects-changed-rank.stderr', source=source))

    def test_repeated_local_dim_reports_reached_resize(self):
        for fixture_name in (
            'shape_1.b',
            'shape_2.b',
            'shape_3.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/routines/repeated-local-dim-reports-reached-resize' / fixture_name
                result = self.run_native(source)
                self.assertEqual((result.returncode, result.stdout), (1, expected_bytes('repeated-local-dim-reports-reached-resize.stdout')))
                self.assertEqual(result.stderr, expected_text('repeated-local-dim-reports-reached-resize.stderr', source=source).encode())

    def test_local_dimension_errors(self):
        cases = [
            ("N = 1.5\nDIM A(N)", expected_text('local-dimension-errors.stderr')),
            ("N = 50000\nDIM A(N,N)", expected_text('local-dimension-errors_2.stderr')),
            ("N = 2\nIF 0 THEN DIM A(N)\nMAT A = 0", expected_text('local-dimension-errors_3.stderr')),
            ("FOR N = 1 TO 2\nDIM A(N)\nNEXT", expected_text('local-dimension-errors_4.stderr')),
            ("N = 2\nDIM A(N)\nN = 3\nA(N) = 1", expected_text('local-dimension-errors_5.stderr')),
        ]
        for case_number, (program, location) in enumerate(cases, 1):
            with self.subTest(program=program):
                source = ROOT / 'tests/routines/local-dimension-errors' / f'bad_{case_number}.b'
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + location).encode(), run.stderr)

    def test_runtime_common_dimension_errors(self):
        cases = [
            ("N = 1.5\nCOMMON A(N)", expected_text('runtime-common-dimension-errors.stderr')),
            ("N = 50000\nCOMMON A(N,N)", expected_text('runtime-common-dimension-errors_2.stderr')),
            ("N = 2\nIF 0 THEN COMMON A(N)\nMAT A = 0", expected_text('runtime-common-dimension-errors_3.stderr')),
            ("FOR N = 1 TO 2\nCOMMON A(N)\nNEXT", expected_text('runtime-common-dimension-errors_4.stderr')),
        ]
        for case_number, (program, location) in enumerate(cases, 1):
            with self.subTest(program=program):
                source = ROOT / 'tests/routines/runtime-common-dimension-errors' / f'bad_{case_number}.b'
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn((str(source) + location).encode(), run.stderr)

    def test_common_runtime_shape_across_routines(self):
        main = ROOT / 'tests/routines/common-runtime-shape-across-routines/main.b'
        sub = ROOT / 'tests/routines/common-runtime-shape-across-routines/sub.b'
        run = self.run_native(main, sub)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('common-runtime-shape-across-routines.stderr', sub=sub).encode(), run.stderr)

    def test_executable_mode(self):
        binary = self.work / 'output with spaces'
        cmd = [CLI, '--exe', ROOT / 'tests/snippets/coercion.b', '-o', binary]
        env = os.environ.copy()
        env.pop('CC', None)
        env.pop('CC_FLAGS', None)
        subprocess.run(cmd, env=env, check=True)
        expected = binary.read_bytes()
        self.assertEqual(subprocess.check_output([binary]), (ROOT / 'tests/snippets/coercion.stdout').read_bytes())

        wrapper = self.work / 'check flags.py'
        wrapper.write_text("import sys\nassert '--argument with spaces' in sys.argv\nsys.exit(42)\n")
        env.update(CC=shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper)),
                   CC_FLAGS="'--argument with spaces'")
        run = subprocess.run(cmd, env=env, text=True, capture_output=True)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('executable-mode.stderr'), run.stderr)
        self.assertEqual(binary.read_bytes(), expected)

    def test_executable_mode_links_math_with_exit_callbacks(self):
        source = ROOT / 'tests/programs/executable-math-and-exit.b'
        wrapper = ROOT / 'tests/io/check-math-link.py'
        binary = self.work / 'program'
        compiler = shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper))
        env = dict(os.environ, CC=compiler, CC_FLAGS='-Wall -Wextra -Werror -pedantic')
        subprocess.run([CLI, '--exe', source, '-o', binary], env=env, check=True)
        run = subprocess.run([binary], capture_output=True, timeout=5, check=True)
        self.assertEqual((run.stdout, run.stderr), (expected_bytes('executable-mode-links-math-with-exit-callbacks.stdout'), b''))

    def test_assignment_predicates_on_arguments(self):
        caller = ROOT / 'tests/programs/assignment-predicates-on-arguments/caller.b'
        sub = ROOT / 'tests/programs/assignment-predicates-on-arguments/init.b'
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('assignment-predicates-on-arguments.stdout'))

    def test_expression_reads_after_conditional_assignment_are_checked_at_runtime(self):
        binary = self.work / 'guard'
        source = ROOT / 'tests/programs/expression-reads-after-conditional-assignment-are-checked-at-runtime.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        for argument, expected in (
            ('hit', (0, expected_bytes('expression-reads-after-conditional-assignment-are-checked-at-runtime.stdout'), b'')),
            ('skip', (0, expected_bytes('expression-reads-after-conditional-assignment-are-checked-at-runtime_2.stdout'), b'')),
            ('broken', (1, b'', expected_text('expression-reads-after-conditional-assignment-are-checked-at-runtime.stderr', source=source).encode())),
        ):
            with self.subTest(argument=argument):
                run = subprocess.run([binary, argument], capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_scalar_reads_after_case_are_checked_at_runtime(self):
        binary = self.work / 'case'
        source = ROOT / 'tests/programs/scalar-reads-after-case-are-checked-at-runtime.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        unassigned = (1, b'', expected_text('scalar-reads-after-case-are-checked-at-runtime.stderr', source=source).encode())
        for argument, expected in (
            ('alpha', (0, expected_bytes('scalar-reads-after-case-are-checked-at-runtime.stdout'), b'')),
            ('beta', (0, expected_bytes('scalar-reads-after-case-are-checked-at-runtime_2.stdout'), b'')),
            ('skip', (0, b'', b'')),
            ('absent', unassigned),
            ('other', unassigned),
        ):
            with self.subTest(argument=argument):
                run = subprocess.run([binary, argument], capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_case_assignment_diagnostics_exclude_unreachable_and_sibling_arms(self):
        for fixture_name, location in (
            ('case_1.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms.stderr')),
            ('case_2.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_2.stderr')),
            ('case_3.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/case-assignment-diagnostics-exclude-unreachable-and-sibling-arms' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_4.stderr', source=source, location=location),
                              result.stderr)

    def test_scalar_reads_after_for_are_checked_at_runtime(self):
        binary = self.work / 'for-loop'
        source = ROOT / 'tests/programs/scalar-reads-after-for-are-checked-at-runtime.b'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                       env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
        unassigned = (1, b'', expected_text('scalar-reads-after-for-are-checked-at-runtime.stderr', source=source).encode())
        for bound, expected in (
            ('-1', (0, b'', b'')),
            ('0', unassigned),
            ('1', (0, expected_bytes('scalar-reads-after-for-are-checked-at-runtime.stdout'), b'')),
            ('2', (0, expected_bytes('scalar-reads-after-for-are-checked-at-runtime_2.stdout'), b'')),
            ('3', unassigned),
            ('4', unassigned),
            ('5', unassigned),
            ('6', (0, expected_bytes('scalar-reads-after-for-are-checked-at-runtime_2.stdout'), b'')),
        ):
            with self.subTest(bound=bound):
                run = subprocess.run([binary, bound], capture_output=True, timeout=5)
                self.assertEqual((run.returncode, run.stdout, run.stderr), expected)

    def test_for_reads_check_values_from_earlier_iterations(self):
        binary = self.work / 'iteration'
        for case_number, branch in enumerate((
            "IF I = 1 THEN Value = 'first' ELSE Value := ':' : I",
            "IF I # 1 THEN Value := ':' : I ELSE Value = 'first'",
        ), 1):
            with self.subTest(branch=branch):
                source = ROOT / 'tests/programs/for-reads-check-values-from-earlier-iterations' / f'iteration_{case_number}.b'
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                               env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
                hit = subprocess.run([binary, '1'], capture_output=True, timeout=5)
                self.assertEqual((hit.returncode, hit.stdout, hit.stderr), (0, expected_bytes('for-reads-check-values-from-earlier-iterations.stdout'), b''))
                miss = subprocess.run([binary, '2'], capture_output=True, timeout=5)
                column = branch.index('Value :=') + 1
                self.assertEqual((miss.returncode, miss.stdout, miss.stderr),
                                 (1, b'', expected_text('for-reads-check-values-from-earlier-iterations.stderr', source=source, column=column).encode()))

    def test_for_reads_without_an_initializer_are_compile_errors(self):
        for fixture_name, column in (
            ('iteration_1.b', 5),
            ('iteration_2.b', 1),
            ('iteration_3.b', 9),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/for-reads-without-an-initializer-are-compile-errors' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(expected_text('for-reads-without-an-initializer-are-compile-errors.stderr', source=source, column=column), result.stderr)
                self.assertIn(expected_text('for-reads-without-an-initializer-are-compile-errors_2.stderr'), result.stderr)

    def test_assignment_probe_does_not_initialize(self):
        for fixture_name, location in (
            ('probe_1.b', expected_text('assignment-probe-does-not-initialize.stderr')),
            ('probe_2.b', expected_text('assignment-probe-does-not-initialize_2.stderr')),
            ('probe_3.b', expected_text('assignment-probe-does-not-initialize_3.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/assignment-probe-does-not-initialize' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(source) + location, result.stderr)

    def test_remove_shared_cursor(self):
        caller = ROOT / 'tests/programs/remove-shared-cursor/caller.b'
        sub = ROOT / 'tests/programs/remove-shared-cursor/take.b'
        run = self.run_native(caller, sub)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('remove-shared-cursor.stdout'))

    def test_remove_expression_diagnostics(self):
        for fixture_name, message in (
            ('bad_1.b', expected_text('remove-expression-diagnostics.stderr')),
            ('bad_2.b', expected_text('remove-expression-diagnostics_2.stderr')),
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/remove-expression-diagnostics' / fixture_name
                result = subprocess.run([CLI, source, '-o', self.c], text=True, capture_output=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(str(source) + message, result.stderr)

    def test_remove_checks_conditionally_assigned_source(self):
        binary = self.work / 'remove'
        fixtures = ROOT / 'tests/programs/remove-checks-conditionally-assigned-source'
        for fixture_name, column in (('statement-first.b', 19), ('expression-first.b', 16)):
            with self.subTest(source=fixture_name):
                source = fixtures / fixture_name
                subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                               env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
                hit = subprocess.run([binary, 'hit'], capture_output=True, timeout=5)
                self.assertEqual((hit.returncode, hit.stdout, hit.stderr),
                                 (0, expected_bytes('remove-checks-conditionally-assigned-source.stdout'), b''))
                miss = subprocess.run([binary, 'miss'], capture_output=True, timeout=5)
                self.assertEqual((miss.returncode, miss.stdout, miss.stderr),
                                 (1, b'', expected_text('remove-checks-conditionally-assigned-source.stderr', source=source, column=column).encode()))

    def test_matrix_assignment_diagnostics(self):
        source = ROOT / 'tests/routines/matrix-assignment-diagnostics/main.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matrix-assignment-diagnostics.stderr', source=source).encode(), run.stderr)
        source = ROOT / 'tests/routines/matrix-assignment-diagnostics/main-variant-2.b'
        run = self.run_native(source)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matrix-assignment-diagnostics_2.stderr', source=source).encode(), run.stderr)

    def test_matrix_fill_evaluates_expression_once(self):
        source = ROOT / 'tests/routines/matrix-fill-evaluates-expression-once/main.b'
        function = ROOT / 'tests/routines/matrix-fill-evaluates-expression-once/BUMP'
        run = self.run_native(source, function)
        self.assertEqual(run.returncode, 0, run.stderr)
        self.assertEqual(run.stdout, expected_bytes('matrix-fill-evaluates-expression-once.stdout'))

    def test_matrix_element_argument_and_bounds(self):
        main = ROOT / 'tests/routines/matrix-element-argument-and-bounds/main.b'
        callee = ROOT / 'tests/routines/matrix-element-argument-and-bounds/put.b'
        run = self.run_native(main, callee)
        self.assertEqual(run.stdout, expected_bytes('matrix-element-argument-and-bounds.stdout'))
        main = ROOT / 'tests/routines/matrix-element-argument-and-bounds/main-variant-2.b'
        run = self.run_native(main)
        self.assertNotEqual(run.returncode, 0)
        self.assertIn(expected_text('matrix-element-argument-and-bounds.stderr', main=main).encode(), run.stderr)

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

    def test_matchfield_invalid_field(self):
        for fixture_name in (
            'matchfield_1.b',
            'matchfield_2.b',
            'matchfield_3.b',
        ):
            with self.subTest(source=fixture_name):
                source = ROOT / 'tests/programs/matchfield-invalid-field' / fixture_name
                run = self.run_native(source)
                self.assertNotEqual(run.returncode, 0)
                self.assertIn(expected_text('matchfield-invalid-field.stderr', source=source).encode(), run.stderr)

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
