import os
import pwd
import select
import subprocess
import time

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_putenv(compiler):
    env = dict(os.environ, JBCC_TEST_PUTENV='inherited')
    env.pop('JBCC_TEST_NEW_ENV', None)
    result = compiler.run_native(ROOT / 'tests/io/putenv.b', env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('putenv.stdout')



def test_host_information_functions(compiler):
    """DELENV, DIR, GETUSERNAME and GETUSERGROUP read the host directly."""
    (compiler.work / 'dir.txt').write_bytes(b'12345')
    (compiler.work / 'sub').mkdir()
    stamp = 1700000000  # 2023-11-14 22:13:20 UTC
    os.utime(compiler.work / 'dir.txt', (stamp, stamp))
    env = dict(os.environ, TZ='UTC', JBCC_TEST_UID=str(os.getuid()))
    result = compiler.run_native(
        ROOT / 'tests/io/host-info.b', cwd=compiler.work, env=env
    )
    assert result.returncode == 0, result.stderr
    lines = result.stdout.split(b'\n')
    assert lines[:3] == [b'110', b'[]00', b'5\xfe20407\xfe80000\xfe']
    assert lines[3].startswith(b'0\xfe') and lines[3].endswith(b'\xfeD')
    assert lines[4:] == [
        b'[]',
        pwd.getpwuid(os.getuid()).pw_name.encode(),
        str(pwd.getpwuid(os.getuid()).pw_gid).encode(),
        b'[]',
        b'',
    ]

def test_getenv(compiler):
    env = dict(os.environ, JBCC_TEST_VALUE='two words', JBCC_TEST_EMPTY='')
    env.pop('JBCC_TEST_ABSENT', None)
    result = compiler.run_native(ROOT / 'tests/io/getenv.b', env=env)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('getenv.stdout')


def test_timezone_variable(compiler, subtests):
    source = ROOT / 'tests/io/timezone.b'
    for env_values, expected in [
        ({'JBASE_TIMEZONE': 'Asia/Tokyo', 'TZ': 'UTC'}, b'[Asia/Tokyo]\n09:00:00\n'),
        ({'TZ': 'Asia/Tokyo'}, b'[Asia/Tokyo]\n09:00:00\n'),
        ({}, b'[]\n'),
    ]:
        with subtests.test(env=env_values):
            env = {
                k: v
                for k, v in os.environ.items()
                if k not in ('JBASE_TIMEZONE', 'TZ')
            }
            env.update(env_values)
            result = compiler.run_native(source, env=env)
            assert result.returncode == 0, result.stderr
            assert result.stdout.startswith(expected)


def test_timediff_month_mask(compiler):
    source = ROOT / 'tests/io/timediff-month-mask.b'
    # Month masks count calendar months, as TAFC PB201214 does
    # (tests/tafc/timediff.b).
    result = compiler.run_native(source)
    assert (result.returncode, result.stderr) == (0, b'')
    assert result.stdout == source.with_suffix('.stdout').read_bytes()


def test_invocation_sentence(compiler, subtests):
    routine = ROOT / 'tests/routines/get.sentence.b'
    binary = compiler.work / 'invocation'
    for case_number, direct_read in enumerate((False, True), 1):
        source = (
            ROOT
            / 'tests/routines/invocation-sentence'
            / f'caller_{case_number}.b'
        )
        subprocess.run(
            [CLI, '--exe', routine, source, '-o', binary], check=True
        )
        for variant, args in enumerate(
            ([], ['42', 'two words', '', 'last']), 1
        ):
            with subtests.test(direct_read=direct_read, args=args):
                run = subprocess.run(
                    ['./invocation', *args],
                    cwd=compiler.work,
                    capture_output=True,
                )
                assert run.returncode == 0, run.stderr
                expected = expected_bytes(
                    f'invocation-sentence_{case_number}_{variant}.stdout'
                )
                assert run.stdout == expected


def test_command_system_variable_uses_the_invocation_in_a_subroutine(
    compiler, subtests
):
    binary = compiler.work / 'invocation'
    source = (
        ROOT
        / 'tests/routines/command-system-variable-uses-the-invocation-in-a-subroutine/caller.b'
    )
    routine = (
        ROOT
        / 'tests/routines/command-system-variable-uses-the-invocation-in-a-subroutine/command.b'
    )
    subprocess.run([CLI, '--exe', routine, source, '-o', binary], check=True)
    for variant, args in enumerate(([], ['first', 'two words', '', 'last']), 1):
        with subtests.test(args=args):
            run = subprocess.run(
                ['./invocation', *args],
                cwd=compiler.work,
                capture_output=True,
                timeout=5,
            )
            expected = expected_bytes(
                f'command-system-variable-uses-the-invocation-in-a-subroutine_{variant}.stdout'
            )
            assert (run.returncode, run.stdout, run.stderr) == (
                0,
                expected,
                b'',
            )


def test_sentence_function_reads_invocation_in_a_subroutine(compiler, subtests):
    binary = compiler.work / 'invocation'
    source = (
        ROOT
        / 'tests/routines/sentence-function-reads-invocation-in-a-subroutine/caller.b'
    )
    routine = (
        ROOT
        / 'tests/routines/sentence-function-reads-invocation-in-a-subroutine/show.b'
    )
    subprocess.run([CLI, '--exe', source, routine, '-o', binary], check=True)
    for variant, args in enumerate(([], ['first', 'two words', '', 'last']), 1):
        with subtests.test(args=args):
            expected = expected_bytes(
                f'sentence-function-reads-invocation-in-a-subroutine_{variant}.stdout'
            )
            run = subprocess.run(
                ['./invocation', *args],
                cwd=compiler.work,
                capture_output=True,
                timeout=5,
            )
            assert (run.returncode, run.stdout, run.stderr) == (
                0,
                expected,
                b'',
            )


def test_parasentence_uses_launch_context_or_invocation(compiler, subtests):
    sources = ROOT / 'tests/routines'
    binary = compiler.work / 'invocation'
    subprocess.run(
        [
            CLI,
            '--exe',
            sources / 'parasentence-main.b',
            sources / 'show-parasentence.b',
            '-o',
            binary,
        ],
        check=True,
    )
    for supplied in (None, '', 'NIGHTLY  REPORT'):
        with subtests.test(supplied=supplied):
            env = dict(os.environ)
            env.pop('JBCC_PARASENTENCE', None)
            if supplied is not None:
                env['JBCC_PARASENTENCE'] = supplied
            invocation = './invocation two words'
            expected = (
                expected_text(
                    'parasentence-uses-launch-context-or-invocation.stdout',
                    value_1=supplied or invocation,
                    invocation=invocation,
                ).encode()
                * 2
            )
            run = subprocess.run(
                ['./invocation', 'two words'],
                cwd=compiler.work,
                env=env,
                capture_output=True,
                timeout=5,
            )
            assert (run.returncode, run.stdout, run.stderr) == (
                0,
                expected,
                b'',
            )


def test_sentence_function_preserves_get_argument_cursor(compiler):
    binary = compiler.work / 'args'
    source = (
        ROOT
        / 'tests/routines/sentence-function-preserves-get-argument-cursor.b'
    )
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    run = subprocess.run(
        [binary, 'one', 'two', 'three'], capture_output=True, timeout=5
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes(
            'sentence-function-preserves-get-argument-cursor.stdout'
        ),
        b'',
    )


def test_sentence_function_diagnostics(compiler, subtests):
    source = ROOT / 'tests/routines/sentence-function-diagnostics/sentence.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'sentence-function-diagnostics.stderr', source=source
        ).encode()
        in result.stderr
    )
    for fixture_name in (
        'sentence-variant-2_1.b',
        'sentence-variant-2_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/routines/sentence-function-diagnostics'
                / fixture_name
            )
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text(
                    'sentence-function-diagnostics_2.stderr', source=source
                ).encode()
                in run.stderr
            )


def test_get_argument_preserves_argv_and_shares_cursor_across_routines(
    compiler,
):
    binary = compiler.work / 'args'
    source = (
        ROOT
        / 'tests/routines/get-argument-preserves-argv-and-shares-cursor-across-routines/args.b'
    )
    routine = (
        ROOT
        / 'tests/routines/get-argument-preserves-argv-and-shares-cursor-across-routines/next.b'
    )
    subprocess.run(
        [CLI, '--exe', source, routine, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    result = subprocess.run(
        [binary, 'first', 'two words', '', 'last'],
        capture_output=True,
        timeout=5,
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'get-argument-preserves-argv-and-shares-cursor-across-routines.stdout'
        ),
        b'',
    )


def test_get_argument_failures_and_diagnostics(compiler):
    source = (
        ROOT / 'tests/routines/get-argument-failures-and-diagnostics/args.b'
    )
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('get-argument-failures-and-diagnostics.stdout'),
        b'',
    )
    source = (
        ROOT
        / 'tests/routines/get-argument-failures-and-diagnostics/args-variant-2.b'
    )
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'get-argument-failures-and-diagnostics.stderr', source=source
        ).encode()
        in result.stderr
    )
    source = (
        ROOT
        / 'tests/routines/get-argument-failures-and-diagnostics/args-variant-3.b'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'get-argument-failures-and-diagnostics_2.stderr', source=source
        )
        in result.stderr
    )


def test_plain_execute_and_perform(compiler):
    run = compiler.run_native(ROOT / 'tests/programs/execute.b')
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('plain-execute-and-perform.stdout')
    assert run.stderr == expected_bytes('plain-execute-and-perform.stderr')


def test_capturing(compiler):
    run = compiler.run_native(ROOT / 'tests/programs/capturing.b')
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('capturing.stdout')
    assert run.stderr == expected_bytes('capturing.stderr')


def test_capture_from_pipe(compiler):
    source = ROOT / 'tests/programs/capture-from-pipe.b'
    binary = compiler.work / 'capture'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    payload = b'x' * (256 * 1024) + b'\r\n\xff'
    run = subprocess.run(
        [binary], input=payload, capture_output=True, timeout=5
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == payload.replace(b'\n', b'\xfe')
    run = subprocess.run(
        [binary], input=b'one\x00two', capture_output=True, timeout=5
    )
    # Byte 0 is kept, as TAFC keeps it (tests/tafc/nul-io.b).
    assert (run.returncode, run.stdout, run.stderr) == (0, b'one\x00two', b'')


def test_exec_rejects_duplicate_returning_clause(compiler):
    source = ROOT / 'tests/programs/exec-rejects-duplicate-returning-clause.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'exec-rejects-duplicate-returning-clause.stderr', source=source
        )
        in result.stderr
    )


def test_execute_large_stdout_and_stderr(compiler):
    source = ROOT / 'tests/programs/execute-large-stdout-and-stderr.b'
    binary = compiler.work / 'execute'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    payload = b'x' * (256 * 1024)
    run = subprocess.run(
        [binary], input=payload, timeout=5, capture_output=True
    )
    assert run.returncode == 0, run.stderr
    assert (
        run.stdout
        == expected_bytes('execute-large-stdout-and-stderr.stdout')
        + b'1\xfe' * 65536
        + b'\n'
        + payload
    )
    assert run.stderr == b''


def test_execute_result_diagnostics(compiler):
    for fixture_name, repeated in (
        ('execute_1.b', 'RETURNING'),
        ('execute_2.b', 'CAPTURING'),
        ('execute_3.b', 'RTNLIST'),
    ):
        source = (
            ROOT / 'tests/programs/execute-result-diagnostics' / fixture_name
        )
        run = subprocess.run(
            [CLI, source, '-o', compiler.c], capture_output=True
        )
        column = source.read_text().rindex(repeated) + 1
        assert run.returncode != 0
        assert (
            expected_text(
                'execute-result-diagnostics.stderr',
                source=source,
                column=column,
                repeated=repeated,
            ).encode()
            in run.stderr
        )
    source = (
        ROOT / 'tests/programs/execute-result-diagnostics/execute-variant-2.b'
    )
    # RETURNING keeps byte 0 from stderr: status 0, a field mark, byte 0.
    run = compiler.run_native(source)
    assert (run.returncode, run.stdout) == (0, b'30FE00\n'), run.stderr



@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('select_1.b', id='select-1'),
        pytest.param('select_2.b', id='select-2'),
        pytest.param('select_3.b', id='select-3'),
        pytest.param('select_4.b', id='select-4'),
        pytest.param('select_5.b', id='select-5'),
        pytest.param('select_6.b', id='select-6'),
    ],
)
def test_execute_rtnlist_forms(compiler, fixture_name):
    """Every RTNLIST form parses, runs the command and continues; the
    variable form gets '' as in TAFC (tests/tafc/execute-passlist.b)."""
    marker = compiler.work / 'child-ran'
    source = ROOT / 'tests/programs/execute-rtnlist-forms' / fixture_name
    run = compiler.run_native(source, cwd=compiler.work)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('execute-rtnlist-forms.stdout')
    assert run.stderr == b''
    assert marker.exists()


def test_execute_child_program(compiler):
    child = ROOT / 'tests/programs/execute-child-program/child.b'
    subprocess.run(
        [CLI, '--exe', child, '-o', compiler.work / 'child'], check=True
    )
    main = ROOT / 'tests/programs/execute-child-program/main.b'
    sub = ROOT / 'tests/programs/execute-child-program/sub.b'
    binary = compiler.work / 'main'
    subprocess.run([CLI, '--exe', main, sub, '-o', binary], check=True)
    run = subprocess.run(
        [binary],
        cwd=compiler.work,
        input=b'hello\n',
        capture_output=True,
        timeout=5,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('execute-child-program.stdout')
    assert run.stderr == b''


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'command_1.b', 'execute-command-diagnostics.stderr', id='command-1'
        ),
        pytest.param(
            'command_2.b',
            'execute-command-diagnostics_2.stderr',
            id='command-2',
        ),
    ],
)
def test_execute_command_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/execute-command-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'execute-command-diagnostics_3.stderr',
            source=source,
            message=message,
        ).encode()
        in run.stderr
    )


def test_account_path_uses_working_directory(compiler):
    source = ROOT / 'tests/programs/account-path-uses-working-directory.b'
    cwd = compiler.work.joinpath(*(['directory-' + 'x' * 60] * 4))
    cwd.mkdir(parents=True)
    env = dict(os.environ, HOME='/unused-home', PWD='/unused-pwd')
    result = compiler.run_native(source, env=env, cwd=cwd)
    assert result.returncode == 0, result.stderr
    assert result.stdout == os.fsencode(cwd.resolve()) + b'\n'
    assert result.stderr == b''


@pytest.mark.parametrize(
    'term',
    [
        pytest.param('xterm-256color', id='xterm-256color'),
        pytest.param('', id='case-2'),
        pytest.param(None, id='case-3'),
    ],
)
def test_terminal_type_aliases_follow_term(compiler, term):
    source = ROOT / 'tests/programs/terminal-type-aliases-follow-term.b'
    env = dict(os.environ)
    if term is None:
        env.pop('TERM', None)
    else:
        env['TERM'] = term
    result = compiler.run_native(source, env=env)
    assert result.returncode == 0, result.stderr
    name = term or ''
    assert (
        result.stdout
        == expected_text(
            'terminal-type-aliases-follow-term.stdout', value_1=name
        ).encode()
    )
    assert result.stderr == b''


@pytest.mark.parametrize(
    'variant, setting',
    [
        pytest.param(1, '00042', id='00042'),
        pytest.param(2, '0', id='0'),
    ],
)
def test_port_number_aliases_use_startup_environment(
    compiler, variant, setting
):
    main = (
        ROOT
        / 'tests/programs/port-number-aliases-use-startup-environment/main.b'
    )
    routine = (
        ROOT
        / 'tests/programs/port-number-aliases-use-startup-environment/show.port.b'
    )
    run = compiler.run_native(
        main, routine, env=dict(os.environ, JBCPORTNO=setting)
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        f'port-number-aliases-use-startup-environment_{variant}.stdout'
    )
    assert run.stderr == b''


def test_pid_uses_native_process_id_with_port_override(compiler):
    source = (
        ROOT / 'tests/programs/pid-uses-native-process-id-with-port-override.b'
    )
    binary = compiler.work / 'pid'
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
    with subprocess.Popen(
        [binary],
        env=dict(os.environ, JBCPORTNO='0'),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=5)
        assert proc.returncode == 0, stderr
        assert (
            stdout
            == expected_text(
                'pid-uses-native-process-id-with-port-override.stdout',
                value_1=proc.pid,
            ).encode()
        )
        assert stderr == b''


def test_user_root_is_shared_with_linked_routines_and_userstats(compiler):
    source = (
        ROOT
        / 'tests/programs/user-root-is-shared-with-linked-routines-and-userstats/main.b'
    )
    routine = (
        ROOT
        / 'tests/programs/user-root-is-shared-with-linked-routines-and-userstats/publish.b'
    )
    run = compiler.run_native(
        source, routine, env=dict(os.environ, JBCPORTNO='1')
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes(
            'user-root-is-shared-with-linked-routines-and-userstats.stdout'
        ),
        b'',
    )


def test_user_root_limit_counts_bytes(compiler):
    source = ROOT / 'tests/programs/user-root-limit-counts-bytes.b'
    run = compiler.run_native(source)
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        b'',
        expected_text(
            'user-root-limit-counts-bytes.stderr', source=source
        ).encode(),
    )


def test_userstats_native_snapshot_and_record_writes(compiler):
    binary = compiler.work / 'stats'
    source = (
        ROOT
        / 'tests/programs/userstats-native-snapshot-and-record-writes/main.b'
    )
    routine = (
        ROOT
        / 'tests/programs/userstats-native-snapshot-and-record-writes/stats.b'
    )
    env = dict(
        os.environ,
        JBCPORTNO='93',
        JBCLOGNAME='stats-user',
        TERM='stats-terminal',
    )
    subprocess.run(
        [
            CLI,
            '--exe',
            '--memory-file',
            'F',
            '--memory-lock',
            'F',
            'held',
            source,
            routine,
            '-o',
            binary,
        ],
        check=True,
        env=dict(env, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    start = int(time.time())
    with subprocess.Popen(
        [binary, 'two words'],
        env=env,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        stdout, stderr = proc.communicate(timeout=5)
        assert (proc.returncode, stderr) == (0, b'')
        lines = stdout.splitlines()
        assert lines[:2] == [
            expected_bytes(
                'userstats-native-snapshot-and-record-writes.stdout'
            ),
            expected_text(
                'userstats-native-snapshot-and-record-writes_2.stdout',
                value_1=proc.pid,
            ).encode(),
        ]
        assert start <= int(lines[2])
        assert int(lines[2]) <= int(time.time())
        assert lines[3:] == [
            expected_bytes(
                'userstats-native-snapshot-and-record-writes_3.stdout'
            ),
            expected_bytes(
                'userstats-native-snapshot-and-record-writes_4.stdout'
            ),
            expected_text(
                'userstats-native-snapshot-and-record-writes_5.stdout',
                binary=binary,
            ).encode(),
            expected_bytes(
                'userstats-native-snapshot-and-record-writes_6.stdout'
            ),
            str(routine).encode(),
        ]


def test_userstats_open_and_read_counters(compiler):
    source = ROOT / 'tests/programs/userstats-open-and-read-counters.b'
    result = compiler.run_native(
        source,
        options=['--memory-file', 'F', '--memory-lock', 'F', 'held'],
        env=dict(os.environ, JBCPORTNO='1'),
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('userstats-open-and-read-counters.stdout'),
        b'',
    )


def test_userstats_delete_and_clearfile_counters(compiler):
    source = ROOT / 'tests/programs/userstats-delete-and-clearfile-counters.b'
    result = compiler.run_native(
        source,
        options=[
            '--memory-file',
            'F',
            '--memory-file',
            'Busy',
            '--memory-lock',
            'Busy',
            'held',
        ],
        env=dict(os.environ, JBCPORTNO='1'),
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('userstats-delete-and-clearfile-counters.stdout'),
        b'',
    )


def test_userstats_execute_and_input_counters(compiler):
    binary = compiler.work / 'terminal-stats'
    source = ROOT / 'tests/programs/userstats-execute-and-input-counters.b'
    env = dict(os.environ, JBCPORTNO='1')
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(env, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    with subprocess.Popen(
        [binary],
        env=env,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ) as proc:
        try:
            expected = expected_bytes(
                'userstats-execute-and-input-counters.stdout'
            )
            received = bytearray()
            while len(received) < len(expected):
                assert select.select([proc.stdout], [], [], 5)[0], received
                chunk = os.read(
                    proc.stdout.fileno(), len(expected) - len(received)
                )
                assert chunk, received
                received.extend(chunk)
            assert received == expected
            proc.stdin.close()
            proc.stdin = None
            output, errors = proc.communicate(timeout=5)
            assert (proc.returncode, output, errors) == (
                0,
                expected_bytes('userstats-execute-and-input-counters_2.stdout'),
                b'',
            )
        finally:
            if proc.poll() is None:
                proc.kill()


def test_userstats_reports_invalid_port_at_reference(compiler):
    source = (
        ROOT / 'tests/programs/userstats-reports-invalid-port-at-reference.b'
    )
    result = compiler.run_native(source, env=dict(os.environ, JBCPORTNO='bad'))
    assert result.returncode != 0
    assert (
        expected_text(
            'userstats-reports-invalid-port-at-reference.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_port_number_defaults_to_process_id(compiler, subtests):
    source = ROOT / 'tests/programs/port-number-defaults-to-process-id.b'
    binary = compiler.work / 'port'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    env = dict(os.environ)
    env.pop('JBCPORTNO', None)
    for empty in (False, True):
        with subtests.test(empty=empty):
            if empty:
                env['JBCPORTNO'] = ''
            with subprocess.Popen(
                [binary],
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            ) as proc:
                stdout, stderr = proc.communicate(timeout=5)
                assert proc.returncode == 0, stderr
                assert stdout == f'{proc.pid}\n{proc.pid}\n'.encode()
                assert stderr == b''


def test_invalid_port_number_reports_call_site(compiler, subtests):
    source = ROOT / 'tests/programs/invalid-port-number-reports-call-site.b'
    for setting in ('12-15', '42,43', '-1', '12.25', '9' * 80):
        with subtests.test(setting=setting):
            run = compiler.run_native(
                source, env=dict(os.environ, JBCPORTNO=setting)
            )
            assert run.returncode != 0
            assert run.stdout == expected_bytes(
                'invalid-port-number-reports-call-site.stdout'
            )
            assert (
                expected_text(
                    'invalid-port-number-reports-call-site.stderr',
                    source=source,
                ).encode()
                in run.stderr
            )


@pytest.mark.parametrize(
    'name, legacy, expected_fixture',
    [
        pytest.param(
            'MainAccount',
            'Fallback',
            'who-uses-startup-login-name.stdout',
            id='mainaccount',
        ),
        pytest.param(
            '',
            'GuideAccount',
            'who-uses-startup-login-name_2.stdout',
            id='case-2',
        ),
    ],
)
def test_who_uses_startup_login_name(compiler, name, legacy, expected_fixture):
    main = ROOT / 'tests/programs/who-uses-startup-login-name/main.b'
    routine = ROOT / 'tests/programs/who-uses-startup-login-name/show.login.b'
    expected = expected_text(expected_fixture)
    env = dict(os.environ, JBCLOGNAME=name, JBASICLOGNAME=legacy)
    run = compiler.run_native(main, routine, env=env)
    assert run.returncode == 0, run.stderr
    assert (
        run.stdout
        == expected_text(
            'who-uses-startup-login-name_3.stdout', expected=expected
        ).encode()
    )
    assert run.stderr == b''


def test_who_defaults_to_posix_user_name(compiler):
    source = ROOT / 'tests/programs/who-defaults-to-posix-user-name.b'
    env = dict(os.environ, USER='different', LOGNAME='different')
    env.pop('JBCLOGNAME', None)
    env.pop('JBASICLOGNAME', None)
    try:
        expected = os.fsencode(pwd.getpwuid(os.getuid()).pw_name)
    except KeyError:
        expected = b''
    run = compiler.run_native(source, env=env)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected + b'\n'
    assert run.stderr == b''


@pytest.mark.parametrize(
    'override, unix_name, account, login',
    [
        pytest.param('Pseudo', 'Unix', 'Pseudo', 'Pseudo', id='pseudo'),
        pytest.param('', 'Unix', 'Unix', 'GuideLogin', id='case-2'),
        pytest.param('', '', 'GuideLogin', 'GuideLogin', id='case-3'),
    ],
)
def test_account_aliases_use_startup_account_name(
    compiler, override, unix_name, account, login
):
    main = (
        ROOT / 'tests/programs/account-aliases-use-startup-account-name/main.b'
    )
    routine = (
        ROOT
        / 'tests/programs/account-aliases-use-startup-account-name/show.account.b'
    )
    env = dict(
        os.environ,
        JBCLOGNAME=override,
        LOGNAME=unix_name,
        JBASICLOGNAME='GuideLogin',
    )
    run = compiler.run_native(main, routine, env=env)
    assert run.returncode == 0, run.stderr
    assert (
        run.stdout
        == expected_text(
            'account-aliases-use-startup-account-name.stdout',
            account=account,
            login=login,
        ).encode()
    )
    assert run.stderr == b''


def test_account_defaults_to_posix_user_name(compiler):
    source = ROOT / 'tests/programs/account-defaults-to-posix-user-name.b'
    env = dict(os.environ)
    for name in ('JBCLOGNAME', 'LOGNAME', 'JBASICLOGNAME'):
        env.pop(name, None)
    try:
        expected = os.fsencode(pwd.getpwuid(os.getuid()).pw_name)
    except KeyError:
        expected = b''
    run = compiler.run_native(source, env=env)
    assert run.returncode == 0, run.stderr
    assert run.stdout == (expected + b'\n') * 2
    assert run.stderr == b''
