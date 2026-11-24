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

    def test_data_queues_input_and_hands_it_to_commands(self):
        source = ROOT / 'tests/io/data-queued-input.b'
        binary = self.work / 'data'
        subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'fallback\n', capture_output=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, expected_bytes('data-queues-input-and-hands-it-to-commands.stdout'))
        self.assertEqual(result.stderr, b'')
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

    def test_cleardata_discards_the_queue_and_preserves_standard_input(self):
        source = ROOT / 'tests/io/cleardata-queued-input.b'
        binary = self.work / 'cleardata'
        subprocess.run([CLI, source, '-o', self.c], check=True)
        subprocess.run(['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic',
                        self.c, '-o', binary], check=True)
        result = subprocess.run([binary], input=b'pipe\n', capture_output=True, timeout=5)
        self.assertEqual((result.returncode, result.stdout, result.stderr),
                         (0, expected_bytes('cleardata-discards-the-queue-and-preserves-standard-input.stdout'), b''))

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
