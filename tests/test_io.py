import fcntl
import os
import select
import subprocess
from datetime import date, datetime

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_display_alias_uses_screen_and_crt_formatting(compiler):
    source = ROOT / 'tests/io/display-screen-formatting.b'
    result = compiler.run_native(
        source, env=dict(os.environ, JBCC_PRINT_DIR=str(compiler.work))
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('display-alias-uses-screen-and-crt-formatting.stdout'),
        b'',
    )
    assert [job.read_bytes() for job in compiler.work.glob('unit-*-*')] == [
        b'printer\n'
    ]

    source = ROOT / 'tests/io/display-unassigned.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'display-alias-uses-screen-and-crt-formatting.stderr', source=source
        )
        in result.stderr
    )


def test_footing_reserves_rows_and_closes_printer_page(compiler):
    source = ROOT / 'tests/io/footing-printer-page.b'
    run = compiler.run_native(
        source, env=dict(os.environ, JBCC_PRINT_DIR=str(compiler.work))
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'footing-reserves-rows-and-closes-printer-page.stdout'
    )
    (job,) = compiler.work.glob('unit-2-*')
    assert job.read_bytes() == b'body\n' + b'\n' * 22 + b'Job    1\n'
    assert run.stderr == b''


def test_sequential_block_io(compiler):
    (compiler.work / 'input').write_bytes(b'a\r\n\xfeend')
    (compiler.work / 'binary').write_bytes(b'x\0yz')
    result = compiler.run_native(
        ROOT / 'tests/io/block-io.b', cwd=compiler.work
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('sequential-block-io.stdout')
    assert (compiler.work / 'output').read_bytes() == b'AXB'
    assert (compiler.work / 'input').read_bytes() == b'a\r\n\xfeend'


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'invalid_1.b', 'block-io-operand-diagnostics.stderr', id='invalid-1'
        ),
        pytest.param(
            'invalid_2.b',
            'block-io-operand-diagnostics_2.stderr',
            id='invalid-2',
        ),
        pytest.param(
            'invalid_3.b',
            'block-io-operand-diagnostics_2.stderr',
            id='invalid-3',
        ),
        pytest.param(
            'invalid_4.b',
            'block-io-operand-diagnostics_3.stderr',
            id='invalid-4',
        ),
    ],
)
def test_block_io_operand_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/io/block-io-operand-diagnostics' / fixture_name
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert (
        expected_text(
            'block-io-operand-diagnostics_4.stderr',
            source=source,
            message=message,
        ).encode()
        in result.stderr
    )


def test_sequential_create_and_truncate(compiler):
    (compiler.work / 'zero').write_bytes(b'old content')
    (compiler.work / 'input').write_bytes(b'keep\n' + b'discard\n' * 2000)
    result = compiler.run_native(
        ROOT / 'tests/io/seq-create.b', cwd=compiler.work
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'sequential-create-and-truncate.stdout'
    )
    assert (compiler.work / 'new').read_bytes() == b'winner\n'
    assert (compiler.work / 'input').read_bytes() == b'keep\nreplacement\n'
    assert (compiler.work / 'empty').read_bytes() == b''
    assert (compiler.work / 'zero').read_bytes() == b''


def test_create_null_handle(compiler):
    source = ROOT / 'tests/io/create-null-handle.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert (
        expected_text('create-null-handle.stderr', source=source).encode()
        in result.stderr
    )


def test_flush_sequential_file(compiler):
    source = ROOT / 'tests/io/flush-sequential-file.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('flush-sequential-file.stdout')
    assert result.stderr == b''


def test_osopen_access_modes_and_osclose_aliases(compiler):
    directory = compiler.work / 'search'
    directory.mkdir()
    data = directory / 'payload'
    data.write_bytes(b'old\nsecond\n')
    source = ROOT / 'tests/io/osopen-access-modes.b'
    result = compiler.run_native(
        source,
        env=dict(os.environ, JEDIFILEPATH=str(directory)),
        cwd=compiler.work,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('osopen-access-modes-and-osclose-aliases.stdout'),
        b'',
    )
    assert data.read_bytes() == b'new\nsecond\n'
    assert not (compiler.work / 'missing').exists()


def test_osclose_invalid_handle_reports_location(compiler):
    source = ROOT / 'tests/io/osclose-invalid-handle.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert (
        expected_text(
            'osclose-invalid-handle-reports-location.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_osbread_offsets_short_reads_and_nul_conversion(compiler):
    (compiler.work / 'data').write_bytes(b'X\0Y\nline\nz')
    source = ROOT / 'tests/io/osbread-offsets.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('osbread-offsets-short-reads-and-nul-conversion.stdout'),
        b'',
    )


def test_osbread_error_arms_and_diagnostic(compiler):
    (compiler.work / 'data').touch()
    source = ROOT / 'tests/io/osbread-errors.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'osbread-error-arms-and-diagnostic.stdout'
    )
    assert (
        expected_text(
            'osbread-error-arms-and-diagnostic.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_osbwrite_round_trips_bytes_and_advances_cursor(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'0123456789')
    source = ROOT / 'tests/io/osbwrite-offsets.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('osbwrite-round-trips-bytes-and-advances-cursor.stdout'),
        b'',
    )
    assert data.read_bytes() == b'01A\x00BC6Z89\x00\x00Q'


def test_osbwrite_error_arms_and_diagnostic(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'unchanged')
    source = ROOT / 'tests/io/osbwrite-errors.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'osbwrite-error-arms-and-diagnostic.stdout'
    )
    assert (
        expected_text(
            'osbwrite-error-arms-and-diagnostic.stderr', source=source
        ).encode()
        in result.stderr
    )
    assert data.read_bytes() == b'unchanged'


def test_oswrite_replaces_appends_and_creates_regular_files(compiler):
    directory = compiler.work / 'search'
    directory.mkdir()
    data = directory / 'payload'
    data.write_bytes(b'old contents that should be replaced')
    (compiler.work / 'empty').write_bytes(b'old')
    source = ROOT / 'tests/io/oswrite-regular-files.b'
    result = compiler.run_native(
        source,
        env=dict(os.environ, JEDIFILEPATH=str(directory)),
        cwd=compiler.work,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'oswrite-replaces-appends-and-creates-regular-files.stdout'
        ),
        b'',
    )
    assert data.read_bytes() == b'new\x00\ntail'
    assert (compiler.work / 'new').read_bytes() == b'created'
    assert (compiler.work / 'empty').read_bytes() == b''
    assert not (compiler.work / 'payload').exists()


def test_oswrite_reports_errors_before_truncating_a_locked_file(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'unchanged')
    source = ROOT / 'tests/io/oswrite-lock-errors.b'
    with data.open('rb') as locked:
        fcntl.flock(locked, fcntl.LOCK_EX)
        result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'oswrite-reports-errors-before-truncating-a-locked-file.stdout'
    )
    assert (
        expected_text(
            'oswrite-reports-errors-before-truncating-a-locked-file.stderr',
            source=source,
        ).encode()
        in result.stderr
    )
    assert data.read_bytes() == b'unchanged'


def test_osdelete_path_resolution_and_status(compiler):
    directory = compiler.work / 'search'
    directory.mkdir()
    for path in (
        compiler.work / 'local',
        directory / 'local',
        directory / 'payload',
        directory / 'explicit',
        directory / 'search',
    ):
        path.write_bytes(b'data')
    source = ROOT / 'tests/io/osdelete-path-resolution.b'
    search_path = f":{compiler.work / 'missing'}::{directory}:"
    result = compiler.run_native(
        source,
        cwd=compiler.work,
        env=dict(os.environ, JEDIFILEPATH=search_path),
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('osdelete-path-resolution-and-status.stdout'),
        b'',
    )
    assert not (compiler.work / 'local').exists()
    assert not (directory / 'payload').exists()
    assert not (directory / 'explicit').exists()
    assert (directory / 'local').read_bytes() == b'data'
    assert (directory / 'search').read_bytes() == b'data'


def test_osdelete_missing_file_and_diagnostics(compiler):
    source = ROOT / 'tests/io/osdelete-missing.b'
    result = compiler.run_native(
        source, cwd=compiler.work, env=dict(os.environ, JEDIFILEPATH='')
    )
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'osdelete-missing-file-and-diagnostics.stdout'
    )
    assert (
        expected_text(
            'osdelete-missing-file-and-diagnostics.stderr', source=source
        ).encode()
        in result.stderr
    )

    source = ROOT / 'tests/io/osdelete-invalid-clause.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'osdelete-missing-file-and-diagnostics_2.stderr', source=source
        )
        in result.stderr
    )


def test_deleteseq_removes_files_and_reports_status(compiler):
    readonly = compiler.work / 'ro'
    readonly.mkdir()
    (readonly / 'c.txt').write_text('three')
    readonly.chmod(0o555)
    try:
        result = compiler.run_native(
            ROOT / 'tests/io/deleteseq.b', cwd=compiler.work
        )
    finally:
        readonly.chmod(0o755)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('deleteseq-removes-files-and-reports-status.stdout'),
        b'',
    )
    assert (readonly / 'c.txt').read_text() == 'three'
    assert not (compiler.work / 'a.txt').exists()
    assert not (compiler.work / 'b.txt').exists()


def test_chdir_changes_the_working_directory(compiler):
    (compiler.work / 'sub').mkdir()
    result = compiler.run_native(ROOT / 'tests/io/chdir.b', cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('chdir-changes-the-working-directory.stdout'),
        b'',
    )
    assert (compiler.work / 'sub/marker').read_text() == 'x'
    assert (compiler.work / 'top').read_text() == 'y'


def test_osread_regular_file_and_error_arms(compiler):
    directory = compiler.work / 'search'
    directory.mkdir()
    (directory / 'payload').write_bytes(b'a' * 5000 + b'\n\0z\n\n')
    (compiler.work / 'empty').touch()
    os.mkfifo(compiler.work / 'fifo')
    source = ROOT / 'tests/io/osread-regular-file.b'
    env = dict(os.environ, JEDIFILEPATH=f'missing-first:{directory}')
    result = compiler.run_native(source, cwd=compiler.work, env=env)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('osread-regular-file-and-error-arms.stdout'),
        b'',
    )


def test_osread_fatal_error_requires_handler(compiler):
    source = ROOT / 'tests/io/osread-unhandled-error.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert result.stdout == b''
    assert (
        expected_text(
            'osread-fatal-error-requires-handler.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_nobuf_uses_unbuffered_sequential_io(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'first\nold\n')
    source = ROOT / 'tests/io/nobuf-sequential-file.b'
    binary = compiler.work / 'nobuf'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    with subprocess.Popen(
        [binary],
        cwd=compiler.work,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        try:
            assert select.select([proc.stdout], [], [], 5)[0]
            assert proc.stdout.readline() == expected_bytes(
                'nobuf-uses-unbuffered-sequential-io.stdout'
            )
            with data.open('r+b') as stream:
                stream.seek(len(b'first\n'))
                stream.write(b'new')
            proc.stdin.write(b'continue\n')
            proc.stdin.flush()
            assert select.select([proc.stdout], [], [], 5)[0]
            assert proc.stdout.readline() == expected_bytes(
                'nobuf-uses-unbuffered-sequential-io_2.stdout'
            )
            assert data.read_bytes() == b'first\nnew\nvisible\n'
            stdout, stderr = proc.communicate(b'done\n', timeout=5)
            assert (proc.returncode, stdout, stderr) == (0, b'', b'')
        finally:
            if proc.poll() is None:
                proc.kill()


def test_nobuf_failure_status_and_diagnostic(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'line\n')
    source = ROOT / 'tests/io/nobuf-errors.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'nobuf-failure-status-and-diagnostic.stdout'
    )
    assert (
        expected_text(
            'nobuf-failure-status-and-diagnostic.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_timeout_on_regular_sequential_file(compiler):
    (compiler.work / 'data').write_bytes(b'line\nblock')
    source = ROOT / 'tests/io/timeout-sequential-file.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'timeout-on-regular-sequential-file.stdout'
    )
    assert result.stderr == b''


@pytest.mark.parametrize(
    'fixture_name, line, message_fixture',
    [
        pytest.param(
            'timeout_1.b', 1, 'timeout-diagnostics.stderr', id='timeout-1'
        ),
        pytest.param(
            'timeout_2.b', 2, 'timeout-diagnostics.stderr', id='timeout-2'
        ),
        pytest.param(
            'timeout_3.b', 3, 'timeout-diagnostics.stderr', id='timeout-3'
        ),
        pytest.param(
            'timeout_4.b', 2, 'timeout-diagnostics_2.stderr', id='timeout-4'
        ),
        pytest.param(
            'timeout_5.b', 2, 'timeout-diagnostics_2.stderr', id='timeout-5'
        ),
        pytest.param(
            'timeout_6.b', 2, 'timeout-diagnostics_2.stderr', id='timeout-6'
        ),
    ],
)
def test_timeout_diagnostics(compiler, fixture_name, line, message_fixture):
    (compiler.work / 'data').write_bytes(b'line\n')
    fixtures = ROOT / 'tests/io/timeout-diagnostics'
    message = expected_text(message_fixture)
    source = fixtures / fixture_name
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert (
        expected_text(
            'timeout-diagnostics_3.stderr',
            source=source,
            line=line,
            message=message,
        ).encode()
        in result.stderr
    )


def test_flush_null_handle(compiler):
    source = ROOT / 'tests/io/flush-null-handle.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('flush-null-handle.stderr', source=source).encode()
        in result.stderr
    )


def test_fileinfo_memory_handle(compiler):
    source = ROOT / 'tests/io/fileinfo-memory-handle.b'
    run = compiler.run_native(source, options=['--memory-file', 'customers'])
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('fileinfo-memory-handle.stdout')
    assert run.stderr == b''


def test_fileinfo_sequential_handle(compiler):
    source = ROOT / 'tests/io/fileinfo-sequential-handle.b'
    run = compiler.run_native(source, cwd=compiler.work)
    assert run.returncode == 0, run.stderr
    path = os.fsencode(compiler.work.resolve() / 'report')
    assert run.stdout == expected_bytes(
        'fileinfo-sequential-handle.stdout'
    ) + path + expected_bytes('fileinfo-sequential-handle_2.stdout')
    assert run.stderr == b''


def test_fileinfo_unsupported_key(compiler):
    source = ROOT / 'tests/io/fileinfo-unsupported-key.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('fileinfo-unsupported-key.stderr', source=source).encode()
        in run.stderr
    )


def test_ioctl_filename_returns_text_and_writes_on_success(compiler):
    source = ROOT / 'tests/io/ioctl-memory-filename.b'
    run = compiler.run_native(source, options=['--memory-file', 'customers'])
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes(
            'ioctl-filename-returns-text-and-writes-on-success.stdout'
        ),
        b'',
    )


def test_ioctl_filename_for_sequential_handle(compiler):
    source = ROOT / 'tests/io/ioctl-sequential-filename.b'
    (compiler.work / 'report').touch()
    run = compiler.run_native(source, cwd=compiler.work)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        os.fsencode(compiler.work.resolve() / 'report')
        + expected_bytes('ioctl-filename-for-sequential-handle.stdout'),
        b'',
    )


def test_ioctl_unsupported_command_diagnostic(compiler):
    source = ROOT / 'tests/io/ioctl-unsupported-command.b'
    run = compiler.run_native(source)
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        b'',
        expected_text(
            'ioctl-unsupported-command-diagnostic.stderr', source=source
        ).encode(),
    )


def test_sequential_seek(compiler):
    path = compiler.work / 'data'
    path.write_bytes(b'abc\n12345\nlast\n')
    result = compiler.run_native(ROOT / 'tests/io/seek.b', cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('sequential-seek.stdout')
    assert path.read_bytes() == b'aZ\n\n12345\nlast\nend\n\x00\x00gap\n'
    assert not (compiler.work / 'absent').exists()


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('invalid_1.b', id='invalid-1'),
        pytest.param('invalid_2.b', id='invalid-2'),
        pytest.param('invalid_3.b', id='invalid-3'),
    ],
)
def test_seek_empty_operands(compiler, fixture_name):
    (compiler.work / 'data').touch()
    source = ROOT / 'tests/io/seek-empty-operands' / fixture_name
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode != 0
    assert (
        expected_text('seek-empty-operands.stderr', source=source).encode()
        in result.stderr
    )


def test_sequential_files(compiler):
    data = b'first\n\n' + b'x' * 1100 + b'\nlast'
    (compiler.work / 'input').write_bytes(data)
    result = compiler.run_native(
        ROOT / 'tests/io/sequential.b', cwd=compiler.work
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('sequential-files.stdout')
    assert (compiler.work / 'input').read_bytes() == data
    assert (compiler.work / 'new').read_bytes() == b'one\nTWO\nlast\nend\n'


def test_sequential_external_lock_and_fifo(compiler):
    source = ROOT / 'tests/io/openseq-external-lock-and-fifo.b'
    os.mkfifo(compiler.work / 'pipe')
    with (compiler.work / 'input').open('wb') as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'sequential-external-lock-and-fifo.stdout'
    )


def test_opendev_regular_file_and_missing_file(compiler):
    data = compiler.work / 'data'
    data.write_bytes(b'first\nsecond\n')
    source = ROOT / 'tests/io/opendev-regular-file.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('opendev-regular-file-and-missing-file.stdout'),
        b'',
    )
    assert data.read_bytes() == b'first\nchange\n'
    assert not (compiler.work / 'missing').exists()


def test_opendev_lock_fallback_and_fifo(compiler):
    data = compiler.work / 'data'
    data.touch()
    os.mkfifo(compiler.work / 'pipe')
    source = ROOT / 'tests/io/opendev-lock-and-fifo.b'
    with data.open('rb') as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('opendev-lock-fallback-and-fifo.stdout'),
        b'',
    )

    source = ROOT / 'tests/io/opendev-missing-branch.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('opendev-lock-fallback-and-fifo.stderr', source=source)
        in result.stderr
    )


def test_ttyget_failure_arms_and_diagnostic(compiler):
    (compiler.work / 'data').touch()
    source = ROOT / 'tests/io/ttyget-errors.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('ttyget-failure-arms-and-diagnostic.stdout'),
        b'',
    )

    source = ROOT / 'tests/io/ttyget-missing-from.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'ttyget-failure-arms-and-diagnostic.stderr', source=source
        )
        in result.stderr
    )


def test_ttyset_failure_arms_and_diagnostic(compiler):
    (compiler.work / 'data').touch()
    source = ROOT / 'tests/io/ttyset-errors.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('ttyset-failure-arms-and-diagnostic.stdout'),
        b'',
    )

    source = ROOT / 'tests/io/ttyset-invalid-on.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'ttyset-failure-arms-and-diagnostic.stderr', source=source
        )
        in result.stderr
    )


def test_sequential_routine_lifetime(compiler):
    (compiler.work / 'input').write_bytes(b'hello\n')
    source = ROOT / 'tests/routines/sequential-lifetime/main.b'
    sub = ROOT / 'tests/routines/sequential-lifetime/opener.b'
    result = compiler.run_native(source, sub, cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('sequential-routine-lifetime.stdout')


def test_saved_lists_across_executables(compiler):
    directory = compiler.work / 'lists'
    directory.mkdir()
    env = dict(os.environ, JBCC_LIST_DIR=str(directory))
    written = compiler.run_native(
        ROOT / 'tests/io/write-lists.b', options=['--memory-file', 'F'], env=env
    )
    assert (written.returncode, written.stdout, written.stderr) == (
        0,
        expected_bytes('saved-lists-across-executables.stdout'),
        b'',
    )
    assert not (compiler.work / 'order').exists()
    read = compiler.run_native(ROOT / 'tests/io/read-lists.b', env=env)
    assert (read.returncode, read.stderr) == (0, b'')
    assert read.stdout == expected_bytes(
        'saved-lists-across-executables_2.stdout'
    )

    deleted = compiler.run_native(ROOT / 'tests/io/delete-lists.b', env=env)
    assert (deleted.returncode, deleted.stderr) == (0, b'')
    assert deleted.stdout == expected_bytes(
        'saved-lists-across-executables_3.stdout'
    )
    check = ROOT / 'tests/io/check-deleted-lists.b'
    after = compiler.run_native(check, env=env)
    assert (after.returncode, after.stdout, after.stderr) == (
        0,
        expected_bytes('saved-lists-across-executables_4.stdout'),
        b'',
    )


def test_selected_tracks_default_external_list_across_calls(compiler):
    main = ROOT / 'tests/routines/selected-list/main.b'
    routine = ROOT / 'tests/routines/selected-list/replace-list.b'
    env = dict(os.environ, JBCC_LIST_DIR=str(compiler.work))
    run = compiler.run_native(main, routine, env=env)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'selected-tracks-default-external-list-across-calls.stdout'
    )
    assert run.stderr == b''


def test_record_id_survives_loop_collection_and_return(compiler):
    main = ROOT / 'tests/routines/record-id/main.b'
    routine = ROOT / 'tests/routines/record-id/select-id.b'
    run = compiler.run_native(main, routine)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'record-id-survives-loop-collection-and-return.stdout'
    )
    assert run.stderr == b''


def test_filename_is_shared_and_independent_of_other_record_context(compiler):
    main = ROOT / 'tests/routines/record-filename/main.b'
    routine = ROOT / 'tests/routines/record-filename/set-filename.b'
    result = compiler.run_native(
        main, routine, options=['--memory-file', 'records']
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'filename-is-shared-and-independent-of-other-record-context.stdout'
        ),
        b'',
    )


def test_record_context_survives_collection_and_changes_only_on_explicit_writes(
    compiler,
):
    main = ROOT / 'tests/routines/record-context/main.b'
    routine = ROOT / 'tests/routines/record-context/seed.b'
    run = compiler.run_native(
        main, routine, options=['--memory-file', 'records']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'record-context-survives-collection-and-changes-only-on-explicit-writes.stdout'
    )
    assert run.stderr == b''


def test_deletelist_requires_named_store(compiler):
    source = ROOT / 'tests/io/deletelist-missing-store.b'
    result = compiler.run_native(source, env=dict(os.environ, JBCC_LIST_DIR=''))
    assert result.returncode != 0
    assert (
        expected_text(
            'deletelist-requires-named-store.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_saved_list_write_failure(compiler):
    source = ROOT / 'tests/io/writelist-missing-directory.b'
    env = dict(os.environ, JBCC_LIST_DIR=str(compiler.work / 'missing'))
    result = compiler.run_native(source, env=env)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('saved-list-write-failure.stdout'),
        b'',
    )


def test_print_units(compiler):
    env = dict(os.environ, JBCC_PRINT_DIR=str(compiler.work))
    result = compiler.run_native(ROOT / 'tests/io/print-units.b', env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('print-units.stdout')
    jobs = sorted(
        (p.name.split('-')[1], p.read_bytes())
        for p in compiler.work.glob('unit-*-*')
    )
    assert jobs == [
        ('0', b'Default 1\nfirst job\n\x0cDefault 2\n'),
        ('127', b'high\n'),
        ('2', b'Other 1\nA\tB\x0cOther 9\nseparate\nReset 1\n'),
        ('2', b'new job\n'),
    ]


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('report_1.b', 'report-diagnostics.stderr', id='report-1'),
        pytest.param('report_2.b', 'report-diagnostics.stderr', id='report-2'),
        pytest.param(
            'report_3.b', 'report-diagnostics_2.stderr', id='report-3'
        ),
        pytest.param('report_4.b', 'report-diagnostics.stderr', id='report-4'),
        pytest.param(
            'report_5.b', 'report-diagnostics_3.stderr', id='report-5'
        ),
        pytest.param(
            'report_6.b', 'report-diagnostics_4.stderr', id='report-6'
        ),
    ],
)
def test_report_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/io/report-diagnostics' / fixture_name
    result = compiler.run_native(
        source, env=dict(os.environ, JBCC_PRINT_DIR='')
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'report-diagnostics_5.stderr', source=source, message=message
        ).encode()
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('rewind_1.b', id='rewind-1'),
        pytest.param('rewind_2.b', id='rewind-2'),
        pytest.param('rewind_3.b', id='rewind-3'),
        pytest.param('rewind_4.b', id='rewind-4'),
    ],
)
def test_rewind_invalid_channel(compiler, fixture_name):
    source = ROOT / 'tests/io/rewind-invalid-channel' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert result.stdout == b''
    assert (
        expected_text('rewind-invalid-channel.stderr', source=source).encode()
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('readt_1.b', id='readt-1'),
        pytest.param('readt_2.b', id='readt-2'),
    ],
)
def test_readt_invalid_channel(compiler, fixture_name):
    source = ROOT / 'tests/io/readt-invalid-channel' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert result.stdout == b''
    assert (
        expected_text('readt-invalid-channel.stderr', source=source).encode()
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('writet_1.b', 'writet-diagnostics.stderr', id='writet-1'),
        pytest.param('writet_2.b', 'writet-diagnostics.stderr', id='writet-2'),
        pytest.param(
            'writet_3.b', 'writet-diagnostics_2.stderr', id='writet-3'
        ),
    ],
)
def test_writet_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/io/writet-diagnostics' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert result.stdout == b''
    assert (str(source) + diagnostic).encode() in result.stderr


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('weof_1.b', id='weof-1'),
        pytest.param('weof_2.b', id='weof-2'),
        pytest.param('weof_3.b', id='weof-3'),
    ],
)
def test_weof_invalid_channel(compiler, fixture_name):
    source = ROOT / 'tests/io/weof-invalid-channel' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert result.stdout == b''
    assert (
        expected_text('weof-invalid-channel.stderr', source=source).encode()
        in result.stderr
    )


def test_memory_files(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/records.b', options=['--memory-file', 'CUSTOMERS']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('memory-files.stdout')


def test_last_file_status(compiler):
    (compiler.work / 'input').write_bytes(b'abc')
    result = compiler.run_native(
        ROOT / 'tests/io/last-file-status.b',
        ROOT / 'tests/io/file-status-probe.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
        cwd=compiler.work,
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('last-file-status.stdout')


def test_status_wrong_argument_count(compiler):
    source = ROOT / 'tests/io/status-wrong-argument-count.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('status-wrong-argument-count.stderr', source=source)
        in result.stderr
    )


def test_record_file_status(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/file-status.b',
        options=['--memory-file', 'data/customers'],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('record-file-status.stdout')


def test_status_empty_descriptor(compiler):
    source = ROOT / 'tests/io/status-empty-descriptor.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('status-empty-descriptor.stderr', source=source).encode()
        in result.stderr
    )


def test_sequential_file_status(compiler):
    path = compiler.work / 'data'
    path.write_bytes(b'one\ntwo\n')
    os.chmod(path, 0o640)
    source = ROOT / 'tests/io/sequential-file-status.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert result.returncode == 0, result.stderr
    st = path.stat()
    identity = [
        st.st_nlink,
        st.st_uid,
        st.st_gid,
        st.st_ino,
        st.st_dev,
        st.st_rdev,
    ]
    times = []
    for seconds in (st.st_mtime_ns // 10**9, st.st_ctime_ns // 10**9):
        t = datetime.fromtimestamp(seconds)
        times.extend(
            [
                t.hour * 3600 + t.minute * 60 + t.second,
                (t.date() - date(1967, 12, 31)).days,
            ]
        )
    assert result.stdout.splitlines() == [
        expected_bytes('sequential-file-status.stdout'),
        ','.join(map(str, identity)).encode(),
        ','.join(map(str, times + [0])).encode(),
        os.fsencode(path.resolve()),
        expected_bytes('sequential-file-status_2.stdout'),
        expected_bytes('sequential-file-status_3.stdout'),
    ]


def test_openpath(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/openpath.b',
        options=[
            '--memory-file',
            'data/customers',
            '--memory-file',
            '/records/customers',
        ],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('openpath.stdout')


def test_record_file_close(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/close.b',
        options=[
            '--memory-file',
            'F',
            '--memory-file',
            'G',
            '--memory-lock',
            'F',
            'foreign',
        ],
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('record-file-close.stdout')


def test_close_by_reference_retires_local_cleanup(compiler):
    main = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/main.b'
    opener = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/opener.b'
    closer = ROOT / 'tests/io/close-by-reference-retires-local-cleanup/closer.b'
    result = compiler.run_native(
        main, opener, closer, options=['--memory-file', 'F']
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'close-by-reference-retires-local-cleanup.stdout'
    )


def test_open_sections(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/open-sections.b',
        options=[
            '--memory-file',
            'CUSTOMERS',
            '--memory-dict',
            'CUSTOMERS',
            '--memory-file',
            'DATA.ONLY',
            '--memory-dict',
            'DICT.ONLY',
        ],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('open-sections.stdout')
    assert run.stderr == b''


def test_delete_records(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/delete.b',
        options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('delete-records.stdout')
    assert run.stderr == b''

    source = ROOT / 'tests/io/delete-records.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('delete-records.stderr', source=source).encode()
        in run.stderr
    )


def test_delete_locked_dispatch(compiler):
    source = ROOT / 'tests/io/delete-locked.b'
    run = compiler.run_native(
        source,
        options=[
            '--memory-file',
            'Records',
            '--memory-lock',
            'Records',
            'busy',
        ],
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('delete-locked-dispatch.stdout'),
        b'',
    )


def test_file_lock_and_unlock(compiler):
    source = ROOT / 'tests/io/file-lock.b'
    options = [
        '--memory-file',
        'Free',
        '--memory-file',
        'Busy',
        '--memory-lock',
        'Busy',
        'held',
    ]
    run = compiler.run_native(source, options=options)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('file-lock-and-unlock.stdout'),
        b'',
    )


def test_clearfile(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/clearfile.b',
        options=['--memory-file', 'CUSTOMERS', '--memory-file', 'OTHER'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('clearfile.stdout')
    assert run.stderr == b''

    source = ROOT / 'tests/io/clearfile/clearfile.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('clearfile.stderr', source=source).encode() in run.stderr
    )


def test_clearfile_locked_dispatch_preserves_records(compiler):
    source = ROOT / 'tests/io/clearfile-locked-dispatch-preserves-records.b'
    result = compiler.run_native(
        source,
        options=[
            '--memory-file',
            'Busy',
            '--memory-file',
            'Free',
            '--memory-lock',
            'Busy',
            'held',
        ],
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('clearfile-locked-dispatch-preserves-records.stdout'),
        b'',
    )


def test_read_setting_uses_record_status_and_branch_order(compiler):
    source = (
        ROOT / 'tests/io/read-setting-uses-record-status-and-branch-order.b'
    )
    result = compiler.run_native(source, options=['--memory-file', 'Sample'])
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'read-setting-uses-record-status-and-branch-order.stdout'
        ),
        b'',
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param(
            'read-setting_1.b',
            'read-setting-requires-destination-and-conditional-arm.stderr',
            id='read-setting-1',
        ),
        pytest.param(
            'read-setting_2.b',
            'read-setting-requires-destination-and-conditional-arm_2.stderr',
            id='read-setting-2',
        ),
    ],
)
def test_read_setting_requires_destination_and_conditional_arm(
    compiler, fixture_name, diagnostic_fixture
):
    diagnostic = expected_text(diagnostic_fixture)
    source = (
        ROOT
        / 'tests/io/read-setting-requires-destination-and-conditional-arm'
        / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert f'{source}{diagnostic}' in result.stderr


def test_readu(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/readu.b',
        ROOT / 'tests/io/reopen.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('readu.stdout')
    assert run.stderr == b''


def test_readu_unhandled_fixture_conflict(compiler):
    source = ROOT / 'tests/io/readu-unhandled-fixture-conflict.b'
    run = compiler.run_native(
        source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy']
    )
    assert run.returncode != 0
    assert (
        expected_text(
            'readu-unhandled-fixture-conflict.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_recordlocku_reserves_key_and_reports_contention(compiler):
    source = ROOT / 'tests/io/recordlocku-reserves-key-and-reports-contention.b'
    run = compiler.run_native(
        source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'recordlocku-reserves-key-and-reports-contention.stdout'
    )
    assert run.stderr == b''


def test_recordlocku_unhandled_contention_reports_call_site(compiler):
    source = (
        ROOT / 'tests/io/recordlocku-unhandled-contention-reports-call-site.b'
    )
    run = compiler.run_native(
        source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy']
    )
    assert run.returncode != 0
    assert (
        expected_text(
            'recordlocku-unhandled-contention-reports-call-site.stderr',
            source=source,
        ).encode()
        in run.stderr
    )


def test_release_on_error_reports_invalid_files_and_preserves_foreign_locks(
    compiler,
):
    source = (
        ROOT
        / 'tests/io/release-on-error-reports-invalid-files-and-preserves-foreign-locks.b'
    )
    result = compiler.run_native(
        source,
        options=(
            '--memory-file',
            'F',
            '--memory-file',
            'G',
            '--memory-lock',
            'F',
            'busy',
        ),
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'release-on-error-reports-invalid-files-and-preserves-foreign-locks.stdout'
        ),
        b'',
    )


def test_assign_system_resets_blocked_record_lock_counter(compiler):
    source = (
        ROOT / 'tests/io/assign-system-resets-blocked-record-lock-counter.b'
    )
    run = compiler.run_native(
        source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'assign-system-resets-blocked-record-lock-counter.stdout'
    )
    assert run.stderr == b''


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param(
            'assign-system_1.b',
            'assign-system-diagnostics.stderr',
            id='assign-system-1',
        ),
        pytest.param(
            'assign-system_2.b',
            'assign-system-diagnostics_2.stderr',
            id='assign-system-2',
        ),
        pytest.param(
            'assign-system_3.b',
            'assign-system-diagnostics_3.stderr',
            id='assign-system-3',
        ),
    ],
)
def test_assign_system_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/io/assign-system-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'assign-system-diagnostics_4.stderr',
            source=source,
            diagnostic=diagnostic,
        ).encode()
        in run.stderr
    )


def test_readv(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/readv.b', options=['--memory-file', 'CUSTOMERS']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('readv.stdout')
    assert run.stderr == b''

    source = ROOT / 'tests/io/readv/readv.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('readv.stderr', source=source).encode() in run.stderr


def test_readvu(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/readvu.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('readvu.stdout')
    assert run.stderr == b''


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('readvu_1.b', 'readvu-diagnostics.stderr', id='readvu-1'),
        pytest.param(
            'readvu_2.b', 'readvu-diagnostics_2.stderr', id='readvu-2'
        ),
    ],
)
def test_readvu_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/io/readvu-diagnostics' / fixture_name
    run = compiler.run_native(
        source, options=['--memory-file', 'F', '--memory-lock', 'F', 'busy']
    )
    assert run.returncode != 0
    assert (
        expected_text(
            'readvu-diagnostics_3.stderr', source=source, diagnostic=diagnostic
        ).encode()
        in run.stderr
    )


def test_write_setting_and_on_error(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/write-error.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('write-setting-and-on-error.stdout')


def test_write_on_error_diagnostics(compiler):
    source = ROOT / 'tests/io/write-on-error-diagnostics/write.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('write-on-error-diagnostics.stderr', source=source)
        in result.stderr
    )
    source = ROOT / 'tests/io/write-on-error-diagnostics/write-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'write-on-error-diagnostics_2.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_writeu(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/writeu.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('writeu.stdout')


def test_writeu_unhandled_failure(compiler):
    source = ROOT / 'tests/io/writeu-unhandled-failure.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('writeu-unhandled-failure.stderr', source=source).encode()
        in result.stderr
    )


def test_writev_and_writevu(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/writev.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('writev-and-writevu.stdout')


@pytest.mark.parametrize(
    'fixture_name, op',
    [
        pytest.param('writev_1.b', 'WRITEV', id='writev-1'),
        pytest.param('writev_2.b', 'WRITEVU', id='writev-2'),
        pytest.param('writev_3.b', 'WRITEV', id='writev-3'),
        pytest.param('writev_4.b', 'WRITEVU', id='writev-4'),
    ],
)
def test_writev_field_number_diagnostics(compiler, fixture_name, op):
    source = ROOT / 'tests/io/writev-field-number-diagnostics' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'writev-field-number-diagnostics.stderr', source=source, op=op
        ).encode()
        in result.stderr
    )


def test_inmat_dimensions_and_latest_load(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/inmat.b',
        ROOT / 'tests/io/inmat-shape.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes(
        'inmat-dimensions-and-latest-load.stdout'
    )


def test_inmat_requires_a_matrix_argument(compiler):
    source = ROOT / 'tests/io/inmat-requires-a-matrix-argument.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('inmat-requires-a-matrix-argument.stderr', source=source)
        in result.stderr
    )


def test_matread(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/matread.b', options=['--memory-file', 'CUSTOMERS']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('matread.stdout')
    assert run.stderr == b''

    source = ROOT / 'tests/io/matread/matread.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert expected_text('matread.stderr', source=source) in run.stderr
    source = ROOT / 'tests/io/matread/matread-variant-2.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert expected_text('matread_2.stderr', source=source) in run.stderr


def test_matreadu(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/matreadu.b',
        options=['--memory-file', 'F', '--memory-lock', 'F', 'busy'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('matreadu.stdout')
    assert run.stderr == b''


def test_matwrite(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/matwrite.b',
        options=['--memory-file', 'EXPLICIT', '--memory-file', 'DEFAULT'],
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('matwrite.stdout')
    assert run.stderr == b''
    source = ROOT / 'tests/io/matwrite/matwrite.b'
    run = compiler.run_native(source, options=['--memory-file', 'F'])
    assert run.returncode != 0
    assert (
        expected_text('matwrite.stderr', source=source).encode() in run.stderr
    )


def test_formlist_rejects_out_of_range_quoted_list_number(compiler):
    source = ROOT / 'tests/programs/formlist-invalid-number.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert (result.returncode, result.stderr) == (
        1,
        expected_text(
            'formlist-rejects-out-of-range-quoted-list-number.stderr',
            source=source,
        ),
    )


def test_file_select(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/select.b', options=['--memory-file', 'F']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('file-select.stdout')
    assert run.stderr == b''
    source = ROOT / 'tests/io/file-select.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert expected_text('file-select.stderr', source=source) in run.stderr


def test_sselect_file(compiler):
    result = compiler.run_native(
        ROOT / 'tests/io/sselect.b', options=['--memory-file', 'F']
    )
    assert result.returncode == 0, result.stderr
    assert result.stderr == b''
    assert result.stdout == expected_bytes('sselect-file.stdout')


def test_sselect_diagnostics(compiler):
    source = ROOT / 'tests/io/sselect-diagnostics/sselect.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert (
        expected_text('sselect-diagnostics.stderr', source=source)
        in result.stderr
    )
    source = ROOT / 'tests/io/sselect-diagnostics/sselect-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('sselect-diagnostics_2.stderr', source=source).encode()
        in run.stderr
    )


def test_clearselect(compiler):
    run = compiler.run_native(
        ROOT / 'tests/io/clearselect.b', options=['--memory-file', 'F']
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('clearselect.stdout')
    assert run.stderr == b''
    source = ROOT / 'tests/io/clearselect/clearselect.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert expected_text('clearselect.stderr', source=source) in run.stderr
    source = ROOT / 'tests/io/clearselect/clearselect-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('clearselect_2.stderr', source=source).encode()
        in run.stderr
    )
