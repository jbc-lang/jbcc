import fcntl
import math
import os
import re
import select
import signal
import struct
import subprocess
import sys
import termios
import time
from datetime import date, datetime, timedelta, timezone
from functools import partial

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_heading_terminal_pause(compiler, request):
    source = ROOT / 'tests/io/heading-terminal-pause.b'
    binary = compiler.work / 'report'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    with subprocess.Popen([binary], stdin=slave, stdout=slave) as proc:
        try:
            output = bytearray()
            while not output.endswith(b'First\r\n'):
                assert select.select([master], [], [], 5)[0], output
                output.extend(os.read(master, 1024))
            assert not select.select([master], [], [], 0.1)[0]
            os.write(master, b'\n')
            assert proc.wait(timeout=5) == 0
            while not output.endswith(b'done\r\n'):
                assert select.select([master], [], [], 5)[0], output
                output.extend(os.read(master, 1024))
            assert expected_bytes('heading-terminal-pause.stdout') in output
        finally:
            proc.kill()


def test_lptrhigh_tracks_current_print_destination(compiler, request):
    source = ROOT / 'tests/io/lptrhigh-print-destination.b'
    binary = compiler.work / 'height'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            compiler.c,
            '-o',
            binary,
        ],
        check=True,
    )
    env = dict(os.environ, JBCC_PRINT_DIR=str(compiler.work))

    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack('HHHH', 42, 80, 0, 0))
    mode = termios.tcgetattr(slave)
    mode[1] &= ~termios.OPOST
    termios.tcsetattr(slave, termios.TCSANOW, mode)
    run = subprocess.run(
        [binary], env=env, stdout=slave, stderr=subprocess.PIPE, timeout=5
    )
    assert (run.returncode, run.stderr) == (0, b'')
    expected = expected_bytes(
        'lptrhigh-tracks-current-print-destination.stdout'
    )
    output = bytearray()
    while len(output) < len(expected):
        assert select.select([master], [], [], 5)[0], output
        output.extend(os.read(master, 1024))
    assert output == expected

    run = subprocess.run([binary], env=env, capture_output=True, timeout=5)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('lptrhigh-tracks-current-print-destination_2.stdout'),
        b'',
    )
    assert [job.read_bytes() for job in compiler.work.glob('unit-7-*')] == [
        b'24\n'
    ] * 2


def test_footing_terminal_pause_and_no_pause(compiler, request):
    source = ROOT / 'tests/io/footing-terminal-pause.b'
    binary = compiler.work / 'footing'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    with subprocess.Popen([binary], stdin=slave, stdout=slave) as proc:
        try:
            first = bytearray()
            while not first.endswith(b'End 1\r\n'):
                assert select.select([master], [], [], 5)[0], first
                first.extend(os.read(master, 1024))
            assert first == expected_bytes(
                'footing-terminal-pause-and-no-pause.stdout'
            )
            assert not select.select([master], [], [], 0.1)[0]
            os.write(master, b'\n')
            assert proc.wait(timeout=5) == 0
            rest = bytearray()
            while not rest.endswith(b'End 3\r\n'):
                assert select.select([master], [], [], 5)[0], rest
                rest.extend(os.read(master, 1024))
            assert (
                expected_bytes('footing-terminal-pause-and-no-pause_2.stdout')
                in rest
            )
            assert rest.endswith(
                expected_bytes('footing-terminal-pause-and-no-pause_3.stdout')
            )
        finally:
            if proc.poll() is None:
                proc.kill()


def test_data_queues_input_and_hands_it_to_commands(compiler):
    source = ROOT / 'tests/io/data-queued-input.b'
    binary = compiler.work / 'data'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    result = subprocess.run(
        [binary], input=b'fallback\n', capture_output=True, timeout=5
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'data-queues-input-and-hands-it-to-commands.stdout'
    )
    assert result.stderr == b''


def test_ttyget_reads_pseudoterminal_settings(compiler, request):
    source = ROOT / 'tests/io/ttyget-settings.b'
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    env = dict(os.environ, JBCC_TEST_PTY=os.ttyname(slave))
    mode = termios.tcgetattr(slave)
    mode[0] = (mode[0] & ~termios.IGNBRK) | termios.BRKINT
    mode[2] = (
        mode[2] & ~(termios.CSIZE | termios.CSTOPB | termios.PARENB)
    ) | termios.CS8
    mode[3] |= termios.ISIG | termios.ICANON | termios.ECHO
    mode[4] = mode[5] = termios.B9600
    termios.tcsetattr(slave, termios.TCSANOW, mode)
    canonical = compiler.run_native(source, env=env)
    assert (canonical.returncode, canonical.stdout, canonical.stderr) == (
        0,
        expected_bytes('ttyget-reads-pseudoterminal-settings.stdout'),
        b'',
    )

    mode[3] &= ~(termios.ICANON | termios.ECHO)
    mode[6][termios.VMIN] = 3
    mode[6][termios.VTIME] = 2
    termios.tcsetattr(slave, termios.TCSANOW, mode)
    noncanonical = compiler.run_native(source, env=env)
    assert (
        noncanonical.returncode,
        noncanonical.stdout,
        noncanonical.stderr,
    ) == (
        0,
        expected_bytes('ttyget-reads-pseudoterminal-settings_2.stdout'),
        b'',
    )

    source = ROOT / 'tests/io/timeout-terminal-handle.b'
    result = compiler.run_native(source, env=env)
    assert result.returncode != 0
    assert (
        expected_text(
            'ttyget-reads-pseudoterminal-settings.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_ttyset_round_trip_and_validation(compiler, request):
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    mode = termios.tcgetattr(slave)
    mode[2] = (
        mode[2] & ~(termios.CSIZE | termios.CSTOPB | termios.PARENB)
    ) | termios.CS8
    mode[3] |= termios.ICANON | termios.ECHO
    mode[4] = mode[5] = termios.B9600
    termios.tcsetattr(slave, termios.TCSANOW, mode)
    original = termios.tcgetattr(slave)
    env = dict(os.environ, JBCC_TEST_PTY=os.ttyname(slave))
    source = ROOT / 'tests/io/ttyset-round-trip.b'
    result = compiler.run_native(source, env=env)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('ttyset-round-trip-and-validation.stdout'),
        b'',
    )
    restored = termios.tcgetattr(slave)
    local_mask = termios.ICANON | termios.ECHO | termios.ISIG
    assert restored[:3] == original[:3]
    assert restored[3] & local_mask == original[3] & local_mask
    assert restored[4:6] == original[4:6]


def test_cleardata_discards_the_queue_and_preserves_standard_input(compiler):
    source = ROOT / 'tests/io/cleardata-queued-input.b'
    binary = compiler.work / 'cleardata'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            compiler.c,
            '-o',
            binary,
        ],
        check=True,
    )
    result = subprocess.run(
        [binary], input=b'pipe\n', capture_output=True, timeout=5
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'cleardata-discards-the-queue-and-preserves-standard-input.stdout'
        ),
        b'',
    )


def test_date_and_time_in_local_timezone(compiler, subtests):
    source = ROOT / 'tests/programs/date-and-time.b'
    binary = compiler.work / 'date'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    epoch = date(1967, 12, 31)
    # These fixed offsets span 24 hours, so a UTC-only implementation fails.
    for zone, offset in [('UTC+10', -10), ('UTC-14', 14)]:
        with subtests.test(zone=zone):
            tz = timezone(timedelta(hours=offset))
            before = datetime.now(tz).replace(microsecond=0)
            run = subprocess.run(
                [binary],
                env=dict(os.environ, TZ=zone),
                capture_output=True,
                text=True,
                check=True,
            )
            after = datetime.now(tz).replace(microsecond=0)
            count, formatted, clock = run.stdout.splitlines()
            assert int(count) in [
                (d.date() - epoch).days for d in (before, after)
            ]
            assert formatted in [
                d.strftime('%m-%d-%Y') for d in (before, after)
            ]
            local_time = datetime.strptime(clock, '%H:%M:%S').time()
            assert any(
                (
                    before
                    <= datetime.combine(d.date(), local_time, tz)
                    <= after
                    for d in (before, after)
                )
            )
            assert run.stderr == ''


def test_timedate_at_local_midnight(compiler):
    source = ROOT / 'tests/programs/timedate-midnight.b'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)

    # Advance one second per read, starting at 2024-01-01 00:59:59 UTC.
    clock = compiler.work / 'clock.c'
    clock.write_text("""#include <time.h>
time_t test_clock(time_t *out)
{
    static time_t next = 1704070799;
    time_t now = next++;
    if (out) *out = now;
    return now;
}
""")
    binary = compiler.work / 'timedate'
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            '-Dtime=test_clock',
            compiler.c,
            clock,
            '-o',
            binary,
        ],
        check=True,
    )
    run = subprocess.run(
        [binary],
        env=dict(os.environ, TZ='UTC+1'),
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout == expected_text('timedate-at-local-midnight.stdout')
    assert run.stderr == ''


def test_timestamp_returns_utc_seconds_at_current_precision(compiler):
    source = ROOT / 'tests/programs/timestamp-clock.b'
    clock = ROOT / 'tests/io/timestamp-clock.c'
    binary = compiler.work / 'timestamp'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            '-Dclock_gettime=test_clock_gettime',
            compiler.c,
            clock,
            '-o',
            binary,
        ],
        check=True,
    )
    run = subprocess.run(
        [binary],
        env=dict(os.environ, TZ='UTC+10'),
        capture_output=True,
        text=True,
        check=True,
    )
    assert run.stdout == expected_text(
        'timestamp-returns-utc-seconds-at-current-precision.stdout'
    )
    assert run.stderr == ''


def test_startup_clock_is_shared_across_midnight(compiler, subtests):
    sources = ROOT / 'tests/routines/startup-clock'
    main = sources / 'main.b'
    # Start one second before midnight in UTC+1.
    clock = compiler.work / 'clock.c'
    clock.write_text("""#include <time.h>
time_t test_clock(time_t *out)
{
    static time_t next = 1704070799;
    time_t now = next++;
    if (out) *out = now;
    return now;
}
""")
    binary = compiler.work / 'startup-clock'
    for name, expected in [
        (
            'date-and-time.b',
            expected_text('startup-clock-is-shared-across-midnight_2.stdout'),
        ),
        (
            'time-only.b',
            expected_text('startup-clock-is-shared-across-midnight_3.stdout'),
        ),
        (
            'date-only.b',
            expected_text('startup-clock-is-shared-across-midnight_4.stdout'),
        ),
    ]:
        with subtests.test(source=name):
            routine = sources / name
            subprocess.run([CLI, main, routine, '-o', compiler.c], check=True)
            subprocess.run(
                [
                    'cc',
                    '-std=c99',
                    '-Wall',
                    '-Wextra',
                    '-Werror',
                    '-pedantic',
                    '-Dtime=test_clock',
                    compiler.c,
                    clock,
                    '-o',
                    binary,
                ],
                check=True,
            )
            run = subprocess.run(
                [binary],
                env=dict(os.environ, TZ='UTC+1'),
                capture_output=True,
                text=True,
                check=True,
            )
            assert (
                run.stdout
                == expected_text(
                    'startup-clock-is-shared-across-midnight.stdout'
                )
                + expected
            )
            assert run.stderr == ''


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'cursor_1.b', 'cursor-coordinate-diagnostics.stderr', id='cursor-1'
        ),
        pytest.param(
            'cursor_2.b',
            'cursor-coordinate-diagnostics_2.stderr',
            id='cursor-2',
        ),
        pytest.param(
            'cursor_3.b',
            'cursor-coordinate-diagnostics_2.stderr',
            id='cursor-3',
        ),
    ],
)
def test_cursor_coordinate_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/io/cursor-coordinate-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'cursor-coordinate-diagnostics_4.stderr',
            source=source,
            message=message,
        ).encode()
        in run.stderr
    )


def test_input_from_pipe(compiler):
    binary = compiler.work / 'input'
    subprocess.run(
        [CLI, '--exe', ROOT / 'tests/io/input.b', '-o', binary], check=True
    )
    first = b'  ' + b'x' * 512 + b'  '
    run = subprocess.run(
        [binary], input=first + b'\n\nlast', capture_output=True, timeout=5
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('input-from-pipe.stdout')
    run = subprocess.run(
        [binary], input=b'a\0b\n', capture_output=True, timeout=5
    )
    assert run.returncode != 0
    assert expected_bytes('input-from-pipe.stderr') in run.stderr


def test_positioned_input_writes_cursor_before_prompt(compiler):
    source = ROOT / 'tests/io/input-positioned.b'
    binary = compiler.work / 'input'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    run = subprocess.run(
        [binary], input=b'first\nsecond\n', capture_output=True, timeout=5
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('positioned-input-writes-cursor-before-prompt.stdout'),
        b'',
    )


def test_length_limited_input_from_pipe(compiler):
    binary = compiler.work / 'input'
    subprocess.run(
        [CLI, '--exe', ROOT / 'tests/io/input-limit.b', '-o', binary],
        check=True,
    )
    run = subprocess.run(
        [binary], input=b'abcde\nx\nend', capture_output=True, timeout=5
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('length-limited-input-from-pipe.stdout')


def test_inputclear_discards_only_terminal_typeahead(
    compiler, subtests, request
):
    binary = compiler.work / 'input'

    def read_until(fd, marker):
        data = bytearray()
        while not data.endswith(marker):
            assert select.select([fd], [], [], 5)[0], data
            data.extend(os.read(fd, 1024))
        return bytes(data)

    for fixture_name in (
        'input_1.b',
        'input_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/io/inputclear-discards-only-terminal-typeahead'
                / fixture_name
            )
            subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
            run = subprocess.run(
                [binary], input=b'pipe\n', capture_output=True, timeout=5
            )
            assert run.returncode == 0, run.stderr
            assert run.stdout == expected_bytes(
                'inputclear-discards-only-terminal-typeahead.stdout'
            )
            assert run.stderr == b''

            master, slave = os.openpty()
            request.addfinalizer(partial(os.close, master))
            request.addfinalizer(partial(os.close, slave))
            mode = termios.tcgetattr(slave)
            mode[3] &= ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(slave, termios.TCSANOW, mode)
            os.write(master, b'stale\npartial')
            assert select.select([slave], [], [], 5)[0]
            with subprocess.Popen(
                [binary], stdin=slave, stdout=slave, stderr=slave
            ) as proc:
                try:
                    assert read_until(master, b'>') == expected_bytes(
                        'inputclear-discards-only-terminal-typeahead_2.stdout'
                    )
                    os.write(master, b'fresh\n')
                    assert read_until(master, b'\r\n') == expected_bytes(
                        'inputclear-discards-only-terminal-typeahead_3.stdout'
                    )
                    assert proc.wait(timeout=5) == 0
                finally:
                    if proc.poll() is None:
                        proc.kill()


def test_input_underscore_discards_excess_in_queue_and_pipe(compiler):
    source = (
        ROOT / 'tests/io/input-underscore-discards-excess-in-queue-and-pipe.b'
    )
    binary = compiler.work / 'input'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    run = subprocess.run(
        [binary], input=b'first\nsecond\nlast', capture_output=True, timeout=5
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'input-underscore-discards-excess-in-queue-and-pipe.stdout'
    )
    assert run.stderr == b''


def test_input_underscore_rings_bell_and_waits_for_enter(compiler, request):
    source = ROOT / 'tests/io/input-underscore-rings-bell-and-waits-for-enter.b'
    binary = compiler.work / 'input'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))

    def read_until(marker):
        data = bytearray()
        while not data.endswith(marker):
            assert select.select([master], [], [], 5)[0], data
            data.extend(os.read(master, 1024))
        return bytes(data)

    with subprocess.Popen(
        [binary], stdin=slave, stdout=slave, stderr=slave
    ) as proc:
        try:
            assert read_until(b'>') == expected_bytes(
                'input-underscore-rings-bell-and-waits-for-enter.stdout'
            )
            os.write(master, b'ab')
            assert read_until(b'\x07') == expected_bytes(
                'input-underscore-rings-bell-and-waits-for-enter_2.stdout'
            )
            os.write(master, b'\n')
            assert read_until(b'\r\n') == expected_bytes(
                'input-underscore-rings-bell-and-waits-for-enter_3.stdout'
            )
            assert proc.wait(timeout=5) == 0
        finally:
            if proc.poll() is None:
                proc.kill()


def test_sleep_duration_and_default(compiler, subtests):
    source = ROOT / 'tests/programs/sleep.b'
    binary = compiler.work / 'pause'
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    for args, minimum in [([], 1.0), (['.15'], 0.15), (['0'], 0)]:
        with subtests.test(args=args):
            start = time.monotonic()
            run = subprocess.run(
                ['pause', *args],
                executable=binary,
                capture_output=True,
                timeout=5,
            )
            assert run.returncode == 0, run.stderr
            assert time.monotonic() - start >= minimum
            assert run.stdout == expected_bytes(
                'sleep-duration-and-default.stdout'
            )
    for value, message in [
        ('-0.1', expected_text('sleep-duration-and-default_2.stderr')),
        ('later', expected_text('sleep-duration-and-default_2.stderr')),
        ('08:30', expected_text('sleep-duration-and-default_3.stderr')),
    ]:
        with subtests.test(value=value):
            run = subprocess.run(
                ['pause', value],
                executable=binary,
                capture_output=True,
                timeout=5,
            )
            assert run.returncode != 0
            assert (
                expected_text(
                    'sleep-duration-and-default.stderr', source=source
                ).encode()
                in run.stderr
            )
            assert message.encode() in run.stderr


def test_msleep_milliseconds_and_default(compiler, subtests):
    source = ROOT / 'tests/programs/msleep.b'
    binary = compiler.work / 'mpause'
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    for args, minimum in [([], 0.001), (['150'], 0.15), (['0'], 0)]:
        with subtests.test(args=args):
            start = time.monotonic()
            run = subprocess.run(
                ['mpause', *args],
                executable=binary,
                capture_output=True,
                timeout=5,
            )
            assert run.returncode == 0, run.stderr
            assert time.monotonic() - start >= minimum
            assert run.stdout == expected_bytes(
                'sleep-duration-and-default.stdout'
            )
    for value in ['-1', 'later']:
        with subtests.test(value=value):
            run = subprocess.run(
                ['mpause', value],
                executable=binary,
                capture_output=True,
                timeout=5,
            )
            assert run.returncode != 0
            assert (
                expected_text(
                    'msleep-milliseconds-and-default.stderr', source=source
                ).encode()
                in run.stderr
            )
            assert (
                expected_text('msleep-milliseconds-and-default_2.stderr').encode()
                in run.stderr
            )


def test_keyin_shares_queued_and_piped_input(compiler):
    binary = compiler.work / 'keyin'
    source = ROOT / 'tests/io/keyin-shares-queued-and-piped-input.b'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    result = subprocess.run(
        [binary], input=b'xyz\n', capture_output=True, timeout=5
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('keyin-shares-queued-and-piped-input.stdout'),
        b'',
    )


def test_keyin_reads_unedited_terminal_byte_and_restores_mode(
    compiler, subtests, request
):
    binary = compiler.work / 'keyin'
    source = (
        ROOT / 'tests/io/keyin-reads-unedited-terminal-byte-and-restores-mode.b'
    )
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    original = termios.tcgetattr(slave)
    original[3] |= termios.ICANON | termios.ECHO | termios.ISIG
    original[6][termios.VERASE] = b'\x7f'
    termios.tcsetattr(slave, termios.TCSANOW, original)

    for value in (b'\x7f', b'\x00', None):
        with subtests.test(value=value), subprocess.Popen(
            [binary],
            stdin=slave,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ) as proc:
            try:
                assert select.select([proc.stdout], [], [], 5)[0]
                assert proc.stdout.readline() == expected_bytes(
                    'keyin-reads-unedited-terminal-byte-and-restores-mode.stdout'
                )
                deadline = time.monotonic() + 5
                while (mode := termios.tcgetattr(slave))[3] & termios.ICANON:
                    assert time.monotonic() < deadline, (
                        'KEYIN did not enter noncanonical mode'
                    )
                    time.sleep(0.01)
                assert not mode[3] & termios.ECHO
                assert mode[3] & termios.ISIG
                if value is None:
                    proc.terminate()
                else:
                    os.write(master, value)
                stdout, stderr = proc.communicate(timeout=5)
                expected = {
                    b'\x7f': (0, b'127\n', b''),
                    b'\x00': (
                        1,
                        b'',
                        f'{source}:2:9: KEYIN cannot store a NUL byte\n'.encode(),
                    ),
                    None: (-signal.SIGTERM, b'', b''),
                }
                assert (proc.returncode, stdout, stderr) == expected[value]
                actual = termios.tcgetattr(slave)
                actual[3] &= ~getattr(termios, 'PENDIN', 0)
                assert actual == original
            finally:
                if proc.poll() is None:
                    proc.kill()


@pytest.mark.parametrize(
    'case_number, function',
    [
        pytest.param(1, 'KEYIN', id='keyin'),
        pytest.param(2, 'IN', id='in'),
    ],
)
def test_keyin_function_diagnostics(compiler, case_number, function):
    source = (
        ROOT / 'tests/io/keyin-function-diagnostics' / f'keyin_{case_number}.b'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'keyin-function-diagnostics.stderr',
            source=source,
            function=function,
        ).encode()
        in result.stderr
    )


def test_timed_input_restarts_after_each_byte(compiler):
    binary = compiler.work / 'input'
    subprocess.run(
        [CLI, '--exe', ROOT / 'tests/io/input-timeout.b', '-o', binary],
        check=True,
    )
    for data in (b'x\n', b'x'):
        run = subprocess.run(
            [binary], input=data, capture_output=True, timeout=5
        )
        assert run.returncode == 0, run.stderr
        assert run.stdout == expected_bytes(
            'timed-input-restarts-after-each-byte.stdout'
        )
    with subprocess.Popen(
        [binary], stdin=subprocess.PIPE, stdout=subprocess.PIPE
    ) as proc:
        try:
            assert select.select([proc.stdout], [], [], 5)[0]
            assert proc.stdout.read(1) == expected_bytes(
                'timed-input-restarts-after-each-byte_2.stdout'
            )
            for byte in (b'a', b'b', b'c'):
                proc.stdin.write(byte)
                proc.stdin.flush()
                if byte != b'c':
                    time.sleep(0.6)
            assert proc.wait(timeout=5) == 0
            assert proc.stdout.read() == expected_bytes(
                'timed-input-restarts-after-each-byte_3.stdout'
            )
        finally:
            proc.kill()


def test_timed_input_diagnostics(compiler):
    source = ROOT / 'tests/io/timed-input-diagnostics/input.b'
    run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True)
    assert run.returncode != 0
    assert (
        expected_text('timed-input-diagnostics.stderr', source=source).encode()
        in run.stderr
    )
    source = ROOT / 'tests/io/timed-input-diagnostics/input-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'timed-input-diagnostics_2.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_input_negative_one_polls_without_consuming_bytes(compiler):
    binary = compiler.work / 'input-poll'
    source = (
        ROOT / 'tests/io/input-negative-one-polls-without-consuming-bytes.b'
    )
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    read_fd, write_fd = os.pipe()
    with os.fdopen(write_fd, 'wb') as writer:
        writer.write(b'z')
    with os.fdopen(read_fd, 'rb') as reader:
        run = subprocess.run(
            [binary], stdin=reader, capture_output=True, timeout=5
        )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes(
            'input-negative-one-polls-without-consuming-bytes.stdout'
        ),
        b'',
    )


def test_input_negative_one_polls_an_empty_open_pipe(compiler):
    binary = compiler.work / 'input-poll'
    source = ROOT / 'tests/io/input-negative-one-polls-an-empty-open-pipe.b'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    with subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        try:
            assert proc.wait(timeout=5) == 0
            assert (proc.stdout.read(), proc.stderr.read()) == (
                expected_bytes(
                    'input-negative-one-polls-an-empty-open-pipe.stdout'
                ),
                b'',
            )
        finally:
            if proc.poll() is None:
                proc.kill()


def test_input_negative_one_detects_terminal_typeahead(compiler, request):
    binary = compiler.work / 'input-poll'
    source = ROOT / 'tests/io/input-negative-one-detects-terminal-typeahead.b'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    original = termios.tcgetattr(slave)
    original[3] |= termios.ICANON
    termios.tcsetattr(slave, termios.TCSANOW, original)
    with subprocess.Popen(
        [binary], stdin=slave, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    ) as proc:
        try:
            assert select.select([proc.stdout], [], [], 5)[0]
            assert proc.stdout.readline() == expected_bytes(
                'input-negative-one-detects-terminal-typeahead.stdout'
            )
            os.write(master, b'q')
            stdout, stderr = proc.communicate(timeout=5)
            assert (proc.returncode, stdout, stderr) == (
                0,
                expected_bytes(
                    'input-negative-one-detects-terminal-typeahead_2.stdout'
                ),
                b'',
            )
            actual = termios.tcgetattr(slave)
            actual[3] &= ~getattr(termios, 'PENDIN', 0)
            assert actual == original
        finally:
            if proc.poll() is None:
                proc.kill()


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'input_1.b', 'input-length-diagnostics.stderr', id='input-1'
        ),
        pytest.param(
            'input_2.b', 'input-length-diagnostics_2.stderr', id='input-2'
        ),
    ],
)
def test_input_length_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/io/input-length-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'input-length-diagnostics_3.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


def test_hush_nonnumeric_operand(compiler):
    source = ROOT / 'tests/io/hush-nonnumeric-operand.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('hush-nonnumeric-operand.stderr', source=source).encode()
        in result.stderr
    )


def test_break_key_controls_terminal_interrupts(compiler, request):
    source = ROOT / 'tests/io/break-key-controls-terminal-interrupts.b'
    binary = compiler.work / 'break-key'
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    mode = termios.tcgetattr(slave)
    mode[3] |= termios.ICANON | termios.ISIG
    mode[6][termios.VINTR] = b'\x03'
    termios.tcsetattr(slave, termios.TCSANOW, mode)

    # Attach the slave as the child's controlling terminal so VINTR sends SIGINT.
    launch = (
        'import fcntl, os, sys, termios\n'
        'fcntl.ioctl(0, termios.TIOCSCTTY, 0)\n'
        'os.execv(sys.argv[1], sys.argv[1:])'
    )
    with subprocess.Popen(
        [sys.executable, '-c', launch, str(binary)],
        stdin=slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    ) as proc:

        def expect_output(expected):
            received = bytearray()
            while len(received) < len(expected):
                assert select.select([proc.stdout], [], [], 5)[0], received
                chunk = os.read(
                    proc.stdout.fileno(), len(expected) - len(received)
                )
                assert chunk, received
                received.extend(chunk)
            assert received == expected

        try:
            expect_output(
                expected_bytes('break-key-controls-terminal-interrupts.stdout')
            )
            os.write(master, b'\x03ok\n')
            expect_output(
                expected_bytes(
                    'break-key-controls-terminal-interrupts_2.stdout'
                )
            )
            os.write(master, b'\x03')
            assert proc.wait(timeout=5) == -signal.SIGINT
            assert proc.stderr.read() == b''
        finally:
            if proc.poll() is None:
                proc.kill()


def test_echo_controls_terminal_input_and_system24(compiler, request):
    source = ROOT / 'tests/io/echo-controls-terminal-input-and-system24.b'
    binary = compiler.work / 'echo'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    original = termios.tcgetattr(slave)

    def read_until(marker):
        data = bytearray()
        while not data.endswith(marker):
            assert select.select([master], [], [], 5)[0], data
            data.extend(os.read(master, 1024))
        return bytes(data)

    with subprocess.Popen(
        [binary], stdin=slave, stdout=slave, stderr=slave
    ) as proc:
        try:
            assert read_until(b'>') == expected_bytes(
                'echo-controls-terminal-input-and-system24.stdout'
            )
            os.write(master, b'secret\n')
            assert read_until(b'>') == expected_bytes(
                'echo-controls-terminal-input-and-system24_2.stdout'
            )
            os.write(master, b'visible\n')
            assert read_until(b'1\r\n0\r\n') == expected_bytes(
                'echo-controls-terminal-input-and-system24_3.stdout'
            )
            assert proc.wait(timeout=5) == 0
            actual = termios.tcgetattr(slave)
            actual[3] &= ~getattr(termios, 'PENDIN', 0)
            assert actual == original
        finally:
            if proc.poll() is None:
                proc.kill()


def test_hush_terminal_input_and_printer(compiler, request):
    source = ROOT / 'tests/io/hush-terminal-input-and-printer.b'
    binary = compiler.work / 'hush'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    env = dict(os.environ, JBCC_PRINT_DIR=str(compiler.work))
    with subprocess.Popen(
        [binary], stdin=slave, stdout=slave, stderr=slave, env=env
    ) as proc:
        try:
            deadline = time.monotonic() + 5
            while termios.tcgetattr(slave)[3] & termios.ECHO:
                assert time.monotonic() < deadline, 'INPUT did not disable echo'
                time.sleep(0.01)
            os.write(master, b'secret\n')
            output = bytearray()
            while not output.endswith(b'?'):
                assert select.select([master], [], [], 5)[0], output
                output.extend(os.read(master, 1024))
            assert output == expected_bytes(
                'hush-terminal-input-and-printer.stdout'
            )
            assert termios.tcgetattr(slave)[3] & termios.ECHO
            os.write(master, b'ok\n')
            assert proc.wait(timeout=5) == 0
        finally:
            proc.kill()
    assert [p.read_bytes() for p in compiler.work.glob('unit-1-*')] == [
        b'job\n'
    ]


def test_input_terminal_echo(compiler, request):
    source = ROOT / 'tests/io/input-terminal-echo.b'
    binary = compiler.work / 'input'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    original = termios.tcgetattr(slave)

    def check_mode_restored():
        actual = termios.tcgetattr(slave)
        # BSD may set the line discipline's pending-input flag on restore.
        actual[3] &= ~getattr(termios, 'PENDIN', 0)
        assert actual == original

    def read_until(marker):
        data = bytearray()
        while not data.endswith(marker):
            assert select.select([master], [], [], 5)[0], data
            data.extend(os.read(master, 1024))
        return bytes(data)

    with subprocess.Popen(
        [binary], stdin=slave, stdout=slave, stderr=slave
    ) as proc:
        try:
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo.stdout'
            )
            os.write(master, b'ax')
            assert read_until(b'x') == expected_bytes(
                'input-terminal-echo_2.stdout'
            )
            os.write(master, original[6][termios.VERASE] + b'b\n')
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo_3.stdout'
            )
            os.write(master, b'c\n')
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo_4.stdout'
            )
            os.write(master, b'xy')
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo_5.stdout'
            )
            os.write(master, b'z')
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo_6.stdout'
            )
            os.write(master, b'ab')
            assert proc.wait(timeout=5) == 0
            assert read_until(b'""\r\n') == expected_bytes(
                'input-terminal-echo_7.stdout'
            )
            check_mode_restored()
        finally:
            proc.kill()

    with subprocess.Popen(
        [binary], stdin=slave, stdout=slave, stderr=slave
    ) as proc:
        try:
            assert read_until(b'?') == expected_bytes(
                'input-terminal-echo.stdout'
            )
            proc.terminate()
            proc.wait(timeout=5)
            check_mode_restored()
        finally:
            proc.kill()


def test_banner(compiler):
    source = ROOT / 'tests/programs/banner.b'
    binary = compiler.work / 'banner'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    home = b'\x1b[H\n'
    blank = expected_bytes('banner.stdout')
    with subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            frames = bytearray()
            while len(frames) < 2 * len(blank):
                assert select.select([process.stdout], [], [], 5)[0], (
                    'frame timeout'
                )
                chunk = os.read(process.stdout.fileno(), 4096)
                assert chunk, 'banner exited before second frame'
                frames.extend(chunk)
            _, err = process.communicate(input=b'q', timeout=5)
            assert process.returncode == 0, err
        finally:
            process.kill()
    assert frames[: len(blank)] == blank
    # Project the fixture's artwork independently at time zero.
    art = re.findall(r'^M\( *\d+\) = "([ X]+)"', source.read_text(), re.M)
    expected = bytearray(home)
    for row in range(24):
        y = 2 * row / 24 - 1
        for col in range(79):
            x = 2 * (col - 39.5) / 79
            scale = 2 / (
                1
                + 0.08 * (math.sin(math.tau * (1 + x)) + math.cos(math.tau * y))
            )
            u = 39.5 + int(0.6 * x * scale * 39.5)
            v = 12 + int(0.6 * y * scale * 12)
            pixel = art[v][int(u)] if 0 <= u < 79 and 0 <= v < 24 else ' '
            expected.append(ord(pixel))
        expected.append(10)
    assert frames[len(blank) : 2 * len(blank)] == expected


def test_snake(compiler, request):
    source = ROOT / 'tests/programs/snake.b'
    binary = compiler.work / 'snake'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    original = termios.tcgetattr(slave)
    original[3] |= termios.ICANON | termios.ECHO
    termios.tcsetattr(slave, termios.TCSANOW, original)
    height, width = 20, 40
    with subprocess.Popen(
        [binary],
        stdin=slave,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            opening = bytearray()
            while opening.count(b'\n') < height + 3:
                assert select.select([process.stdout], [], [], 10)[0], (
                    'board timeout'
                )
                chunk = os.read(process.stdout.fileno(), 4096)
                assert chunk, 'snake exited before drawing the board'
                opening.extend(chunk)
            os.write(master, b's')
            output = bytearray()
            deadline = time.monotonic() + 5
            while b'v' not in output:
                remaining = deadline - time.monotonic()
                assert (
                    remaining > 0
                    and select.select([process.stdout], [], [], remaining)[0]
                ), 'snake did not turn after a single s keystroke'
                chunk = os.read(process.stdout.fileno(), 4096)
                assert chunk, 'snake exited before turning'
                output.extend(chunk)
            os.write(master, b'q')
            _, err = process.communicate(timeout=5)
            assert (process.returncode, err) == (1, b'')
            actual = termios.tcgetattr(slave)
            actual[3] &= ~getattr(termios, 'PENDIN', 0)
            assert actual == original
        finally:
            if process.poll() is None:
                process.kill()
    instructions, *board = opening.splitlines()[: height + 3]
    assert instructions == (
        b'\x1b[H\x1b[JWASD: w up, a left, s down, d right | q quit'
    )
    assert board[0] == board[-1] == b'#' * (width + 2)
    assert all(len(row) == width + 2 for row in board)
    assert b'@>' in board[1]


def test_life(compiler):
    source = ROOT / 'tests/programs/life.b'
    binary = compiler.work / 'life'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)

    # The glider moves and the blinker turns vertical after one generation.
    generations = (
        {(3, 2), (4, 3), (2, 4), (3, 4), (4, 4), (19, 15), (20, 15), (21, 15)},
        {(2, 3), (4, 3), (3, 4), (4, 4), (3, 5), (20, 14), (20, 15), (20, 16)},
    )
    expected = b'\x1b[H\x1b[J'
    for live in generations:
        expected += b'\x1b[H' + b'\n'.join(
            bytes(
                ord('O') if (x, y) in live else ord('.') for x in range(1, 41)
            )
            for y in range(1, 31)
        )

    with subprocess.Popen(
        [binary],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as process:
        try:
            frames = bytearray()
            while len(frames) < len(expected):
                assert select.select([process.stdout], [], [], 5)[0], (
                    'Life frame timeout'
                )
                chunk = os.read(process.stdout.fileno(), 4096)
                assert chunk, 'Life exited before drawing two frames'
                frames.extend(chunk)
            _, stderr = process.communicate(input=b'q', timeout=5)
            assert (process.returncode, stderr) == (0, b'')
        finally:
            if process.poll() is None:
                process.kill()
    assert frames[: len(expected)] == expected


def test_system14_input_queue(compiler):
    source = ROOT / 'tests/io/system14-input-queue.b'
    binary = compiler.work / 'pending'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            compiler.c,
            '-o',
            binary,
        ],
        check=True,
    )
    with open(os.devnull, 'rb') as empty:
        result = subprocess.run(
            [binary], stdin=empty, capture_output=True, timeout=5
        )
        assert (result.returncode, result.stdout, result.stderr) == (
            0,
            expected_bytes('system14-input-queue.stdout'),
            b'',
        )
    # Preload the pipe before starting the program. Polling leaves its bytes queued.
    read_fd, write_fd = os.pipe()
    with os.fdopen(write_fd, 'wb') as writer:
        writer.write(b'abc')
    with os.fdopen(read_fd, 'rb') as reader:
        result = subprocess.run(
            [binary], stdin=reader, capture_output=True, timeout=5
        )
        assert (result.returncode, result.stdout, result.stderr) == (
            0,
            expected_bytes('system14-input-queue_2.stdout'),
            b'',
        )


def test_tty_name_with_terminal_and_redirected_input(
    compiler, subtests, request
):
    source = (
        ROOT / 'tests/programs/tty-name-with-terminal-and-redirected-input.b'
    )
    binary = compiler.work / 'tty'
    subprocess.run([CLI, source, '-o', compiler.c], check=True)
    subprocess.run(
        [
            'cc',
            '-std=c99',
            '-Wall',
            '-Wextra',
            '-Werror',
            '-pedantic',
            compiler.c,
            '-o',
            binary,
        ],
        check=True,
    )

    master, slave = os.openpty()
    request.addfinalizer(partial(os.close, master))
    request.addfinalizer(partial(os.close, slave))
    terminal = os.fsencode(os.ttyname(slave))
    for stdin, expected in (
        (slave, terminal),
        (
            subprocess.DEVNULL,
            expected_bytes(
                'tty-name-with-terminal-and-redirected-input_2.stdout'
            ),
        ),
    ):
        with subtests.test(stdin=stdin):
            run = subprocess.run(
                [binary], stdin=stdin, capture_output=True, timeout=5
            )
            assert run.returncode == 0, run.stderr
            assert (
                run.stdout
                == expected_bytes(
                    'tty-name-with-terminal-and-redirected-input.stdout'
                )
                + expected
                + expected_bytes(
                    'tty-name-with-terminal-and-redirected-input_3.stdout'
                )
                + expected[:1]
                + b'\n'
            )
            assert run.stderr == b''
