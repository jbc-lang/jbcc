import os
import shlex
import subprocess
import sys

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_logical_function_calls(compiler):
    main = ROOT / 'tests/routines/logical-calls/main.b'
    function = ROOT / 'tests/routines/logical-calls/bump.b'
    run = compiler.run_native(main, function)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('logical-function-calls.stdout')
    main = ROOT / 'tests/routines/logical-calls/unassigned.b'
    run = subprocess.run(
        [CLI, main, function, '-o', compiler.c], text=True, capture_output=True
    )
    assert run.returncode != 0
    assert (
        expected_text('logical-function-calls.stderr', main=main) in run.stderr
    )


def test_conditional_expression_calls(compiler):
    main = ROOT / 'tests/routines/conditional-calls/main.b'
    function = ROOT / 'tests/routines/conditional-calls/bump.b'
    run = compiler.run_native(main, function)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('conditional-expression-calls.stdout'),
        b'',
    )

    main = ROOT / 'tests/routines/conditional-calls/unassigned.b'
    run = subprocess.run(
        [CLI, main, function, '-o', compiler.c], text=True, capture_output=True
    )
    assert run.returncode != 0
    assert (
        expected_text('conditional-expression-calls.stderr', main=main)
        in run.stderr
    )


@pytest.mark.parametrize(
    'case_number, ending, status',
    [
        pytest.param(1, '', 0, id='case-1'),
        pytest.param(2, 'STOP', 0, id='stop'),
        pytest.param(3, 'EXIT(7)', 7, id='exit-7'),
        pytest.param(4, 'ABORT', 1, id='abort'),
        pytest.param(5, 'DEBUG', 1, id='debug'),
    ],
)
def test_callonexit_dispatches_linked_callbacks(
    compiler, case_number, ending, status
):
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
    source = (
        ROOT
        / 'tests/routines/callonexit-dispatches-linked-callbacks'
        / f'exit_{case_number}.b'
    )
    result = compiler.run_native(source, save, show, wrong)
    assert result.returncode == status, result.stderr
    assert result.stdout == expected_bytes(
        'callonexit-dispatches-linked-callbacks.stdout'
    )
    if ending == 'DEBUG':
        assert (
            expected_bytes('callonexit-dispatches-linked-callbacks.stderr')
            in result.stderr
        )
    else:
        assert result.stderr == b''


def test_external_subroutine(compiler):
    directory = ROOT / 'tests/routines'
    run = compiler.run_native(
        directory / 'caller.b', directory / 'get.status.b'
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('external-subroutine.stdout')


def test_bang_subroutine_names(compiler):
    main = ROOT / 'tests/routines/bang-subroutine-names/main.b'
    plain = ROOT / 'tests/routines/bang-subroutine-names/plain.b'
    bang = ROOT / 'tests/routines/bang-subroutine-names/bang.b'
    run = compiler.run_native(main, plain, bang)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('bang-subroutine-names.stdout')
    assert run.stderr == b''


def test_call_aliases_and_expression_arguments(compiler):
    caller = (
        ROOT / 'tests/routines/call-aliases-and-expression-arguments/caller.b'
    )
    callee = (
        ROOT / 'tests/routines/call-aliases-and-expression-arguments/callee.b'
    )
    run = compiler.run_native(callee, caller)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'call-aliases-and-expression-arguments.stdout'
    )


def test_indirect_call(compiler):
    main = ROOT / 'tests/routines/indirect-call/main.b'
    work = ROOT / 'tests/routines/indirect-call/work.b'
    switch = ROOT / 'tests/routines/indirect-call/switch.b'
    done = ROOT / 'tests/routines/indirect-call/done.b'
    run = compiler.run_native(main, work, switch, done)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('indirect-call.stdout')
    assert run.stderr == b''


def test_empty_actual_uses_local_storage_for_mat_formal(compiler):
    main = (
        ROOT
        / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/main.b'
    )
    load = (
        ROOT
        / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/load.b'
    )
    scalar = (
        ROOT
        / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/scalar.b'
    )
    result = compiler.run_native(main, load, scalar)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('empty-actual-uses-local-storage-for-mat-formal.stdout'),
        b'',
    )


def test_empty_mat_actual_requires_dimension_before_use(compiler):
    main = (
        ROOT
        / 'tests/routines/empty-mat-actual-requires-dimension-before-use/main.b'
    )
    load = (
        ROOT
        / 'tests/routines/empty-mat-actual-requires-dimension-before-use/load.b'
    )
    result = compiler.run_native(main, load)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        b'',
        expected_text(
            'empty-mat-actual-requires-dimension-before-use.stderr', load=load
        ).encode(),
    )


def test_callc_subroutine_exists_checks_linked_subroutines(compiler):
    main = (
        ROOT
        / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main.b'
    )
    subroutine = (
        ROOT
        / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/worker.b'
    )
    function = (
        ROOT
        / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/compute.b'
    )
    result = compiler.run_native(main, subroutine, function)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'callc-subroutine-exists-checks-linked-subroutines.stdout'
        ),
        b'',
    )

    main = (
        ROOT
        / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main-variant-2.b'
    )
    result = compiler.run_native(main)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'callc-subroutine-exists-checks-linked-subroutines_2.stdout'
        ),
        b'',
    )


@pytest.mark.parametrize(
    'case_number, arguments, marker, message_fixture',
    [
        pytest.param(
            1,
            "'WORKER'",
            ')',
            'callc-subroutine-exists-requires-two-arguments.stderr',
            id='worker',
        ),
        pytest.param(
            2,
            "'WORKER', Info, 0",
            ', 0',
            'callc-subroutine-exists-requires-two-arguments_2.stderr',
            id='worker-info-0',
        ),
    ],
)
def test_callc_subroutine_exists_requires_two_arguments(
    compiler, case_number, arguments, marker, message_fixture
):
    message = expected_text(message_fixture)
    statement = f'CRT CALLC JBASESubroutineExist({arguments})'
    source = (
        ROOT
        / 'tests/routines/callc-subroutine-exists-requires-two-arguments'
        / f'main_{case_number}.b'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'callc-subroutine-exists-requires-two-arguments_3.stderr',
            source=source,
            value_2=statement.rindex(marker) + 1,
            message=message,
        )
        in result.stderr
    )


def test_call_expands_equates_in_arguments_and_indirect_targets(compiler):
    main = (
        ROOT
        / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/main.b'
    )
    direct = (
        ROOT
        / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/direct.b'
    )
    prefixed = (
        ROOT
        / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/prefixed.b'
    )
    run = compiler.run_native(main, direct, prefixed)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes(
            'call-expands-equates-in-arguments-and-indirect-targets.stdout'
        ),
        b'',
    )


def test_quoted_and_punctuated_direct_routine_names(compiler):
    main = (
        ROOT
        / 'tests/routines/quoted-and-punctuated-direct-routine-names/main.b'
    )
    star = (
        ROOT
        / 'tests/routines/quoted-and-punctuated-direct-routine-names/star.b'
    )
    dashed = (
        ROOT
        / 'tests/routines/quoted-and-punctuated-direct-routine-names/dashed.b'
    )
    quoted_header = (
        ROOT
        / 'tests/routines/quoted-and-punctuated-direct-routine-names/quoted.b'
    )
    result = compiler.run_native(main, star, dashed, quoted_header)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('quoted-and-punctuated-direct-routine-names.stdout'),
        b'',
    )


def test_quoted_direct_target_preserves_whitespace_and_punctuation(compiler):
    main = (
        ROOT
        / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main.b'
    )
    result = subprocess.run(
        [CLI, main, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'quoted-direct-target-preserves-whitespace-and-punctuation.stderr',
        main=main,
    )

    main = (
        ROOT
        / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main-variant-2.b'
    )
    result = subprocess.run(
        [CLI, main, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'quoted-direct-target-preserves-whitespace-and-punctuation_2.stderr',
        main=main,
    )


def test_indirect_call_diagnostics(compiler, subtests):
    fixtures = ROOT / 'tests/routines/indirect-call-diagnostics'
    sub = fixtures / 'update.b'
    for fixture_name, name, units, message in (
        (
            'main_1.b',
            'MISSING',
            (),
            expected_text('indirect-call-diagnostics.stderr'),
        ),
        (
            'main_2.b',
            'update',
            (sub,),
            expected_text('indirect-call-diagnostics.stderr'),
        ),
        (
            'main_3.b',
            'UPDATE',
            (sub,),
            expected_text('indirect-call-diagnostics_2.stderr'),
        ),
        (
            'main_4.b',
            'UPDATE',
            (sub,),
            expected_text('indirect-call-diagnostics_2.stderr'),
        ),
    ):
        with subtests.test(source=fixture_name):
            main = fixtures / fixture_name
            run = compiler.run_native(main, *units)
            assert run.returncode != 0
            assert run.stdout == b''
            assert (
                expected_text(
                    'indirect-call-diagnostics_3.stderr',
                    main=main,
                    message=message,
                    value_3=name,
                ).encode()
                in run.stderr
            )


def test_indirect_call_through_matrix_element(compiler):
    main = ROOT / 'tests/routines/indirect-call-through-matrix-element/main.b'
    add = ROOT / 'tests/routines/indirect-call-through-matrix-element/add.b'
    report = (
        ROOT / 'tests/routines/indirect-call-through-matrix-element/report.b'
    )
    change = (
        ROOT / 'tests/routines/indirect-call-through-matrix-element/change.b'
    )
    result = compiler.run_native(main, add, report, change)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('indirect-call-through-matrix-element.stdout'),
        b'',
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'main_1.b',
            'indirect-matrix-call-uses-normal-matrix-diagnostics.stderr',
            id='main-1',
        ),
        pytest.param(
            'main_2.b',
            'indirect-matrix-call-uses-normal-matrix-diagnostics_2.stderr',
            id='main-2',
        ),
    ],
)
def test_indirect_matrix_call_uses_normal_matrix_diagnostics(
    compiler, fixture_name, message_fixture
):
    message = expected_text(message_fixture)
    source = (
        ROOT
        / 'tests/routines/indirect-matrix-call-uses-normal-matrix-diagnostics'
        / fixture_name
    )
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == b''
    assert (
        expected_text(
            'indirect-matrix-call-uses-normal-matrix-diagnostics_3.stderr',
            source=source,
            message=message,
        ).encode()
        in result.stderr
    )


def test_multiline_call(compiler):
    caller = ROOT / 'tests/routines/multiline-call/caller.b'
    callee = ROOT / 'tests/routines/multiline-call/callee.b'
    run = compiler.run_native(caller, callee)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('multiline-call.stdout')


def test_external_function(compiler):
    directory = ROOT / 'tests/routines'
    binary = compiler.work / 'program'
    subprocess.run(
        [
            CLI,
            '--exe',
            directory / 'function.caller.b',
            directory / 'DOUBLE.IT',
            '-o',
            binary,
        ],
        check=True,
    )
    assert subprocess.check_output([binary]) == expected_bytes(
        'external-function.stdout'
    )


def test_deffun_call_as_statement_discards_return_and_updates_argument(
    compiler,
):
    main = (
        ROOT
        / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/main.b'
    )
    function = (
        ROOT
        / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/function.b'
    )
    result = compiler.run_native(main, function)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'deffun-call-as-statement-discards-return-and-updates-argument.stdout'
        ),
        b'',
    )


def test_function_arguments_and_returns(compiler):
    main = ROOT / 'tests/routines/function-arguments-and-returns/main.b'
    inc = ROOT / 'tests/routines/function-arguments-and-returns/INC'
    empty = ROOT / 'tests/routines/function-arguments-and-returns/EMPTY'
    run = compiler.run_native(empty, inc, main)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('function-arguments-and-returns.stdout')


def test_matrix_parameters(compiler):
    main = ROOT / 'tests/routines/matrix-parameters/main.b'
    sub = ROOT / 'tests/routines/matrix-parameters/relay.b'
    func = ROOT / 'tests/routines/matrix-parameters/edit.b'
    run = compiler.run_native(main, sub, func)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('matrix-parameters.stdout')


def test_matrix_parameter_diagnostics(compiler):
    for case_number, (call, formal) in enumerate(
        [('CALL S(MAT A)', 'X'), ('CALL S(N)', 'MAT X')], 1
    ):
        main = (
            ROOT
            / 'tests/routines/matrix-parameter-diagnostics'
            / f'main_{case_number}.b'
        )
        sub = (
            ROOT
            / 'tests/routines/matrix-parameter-diagnostics'
            / f'sub_{case_number}.b'
        )
        result = subprocess.run(
            [CLI, main, sub, '-o', compiler.c], text=True, capture_output=True
        )
        assert result.returncode != 0
        assert (
            expected_text('matrix-parameter-diagnostics.stderr', main=main)
            in result.stderr
        )
    main = ROOT / 'tests/routines/matrix-parameter-diagnostics/main-variant-2.b'
    for fixture_name, message in (
        (
            'sub-variant-2_1.b',
            expected_text('matrix-parameter-diagnostics_3.stderr'),
        ),
        (
            'sub-variant-2_2.b',
            expected_text('matrix-parameter-diagnostics_4.stderr'),
        ),
        (
            'sub-variant-2_3.b',
            expected_text('matrix-parameter-diagnostics_5.stderr'),
        ),
    ):
        sub = (
            ROOT / 'tests/routines/matrix-parameter-diagnostics' / fixture_name
        )
        run = compiler.run_native(main, sub)
        assert run.returncode != 0
        assert (
            expected_text(
                'matrix-parameter-diagnostics_2.stderr', sub=sub
            ).encode()
            in run.stderr
        )
        assert message.encode() in run.stderr


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('main_1.b', 'function-diagnostics.stderr', id='main-1'),
        pytest.param('main_2.b', 'function-diagnostics_2.stderr', id='main-2'),
        pytest.param('main_3.b', 'function-diagnostics_3.stderr', id='main-3'),
        pytest.param('main_4.b', 'function-diagnostics_4.stderr', id='main-4'),
    ],
)
def test_function_diagnostics(compiler, fixture_name, message_fixture):
    definition = ROOT / 'tests/routines/DOUBLE.IT'
    message = expected_text(message_fixture)
    main = ROOT / 'tests/routines/function-diagnostics' / fixture_name
    run = subprocess.run(
        [CLI, main, definition, '-o', compiler.c],
        capture_output=True,
        text=True,
    )
    assert run.returncode != 0
    assert str(main) + message in run.stderr


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('main_1.b', 'bad-routine-references.stderr', id='main-1'),
        pytest.param(
            'main_2.b', 'bad-routine-references_2.stderr', id='main-2'
        ),
        pytest.param(
            'main_3.b', 'bad-routine-references_3.stderr', id='main-3'
        ),
        pytest.param(
            'main_4.b', 'bad-routine-references_4.stderr', id='main-4'
        ),
        pytest.param(
            'main_5.b', 'bad-routine-references_5.stderr', id='main-5'
        ),
        pytest.param(
            'main_6.b', 'bad-routine-references_6.stderr', id='main-6'
        ),
        pytest.param(
            'main_7.b', 'bad-routine-references_7.stderr', id='main-7'
        ),
        pytest.param(
            'main_8.b', 'bad-routine-references_8.stderr', id='main-8'
        ),
        pytest.param(
            'main_9.b', 'bad-routine-references_9.stderr', id='main-9'
        ),
        pytest.param(
            'main_10.b', 'bad-routine-references_10.stderr', id='main-10'
        ),
        pytest.param(
            'main_11.b', 'bad-routine-references_11.stderr', id='main-11'
        ),
        pytest.param(
            'main_12.b', 'bad-routine-references_12.stderr', id='main-12'
        ),
        pytest.param(
            'main_13.b', 'bad-routine-references_13.stderr', id='main-13'
        ),
        pytest.param(
            'main_14.b', 'bad-routine-references_9.stderr', id='main-14'
        ),
        pytest.param(
            'main_15.b', 'bad-routine-references_14.stderr', id='main-15'
        ),
        pytest.param(
            'main_16.b', 'bad-routine-references_5.stderr', id='main-16'
        ),
        pytest.param(
            'main_17.b', 'bad-routine-references_15.stderr', id='main-17'
        ),
        pytest.param(
            'main_18.b', 'bad-routine-references_16.stderr', id='main-18'
        ),
    ],
)
def test_bad_routine_references(compiler, fixture_name, message_fixture):
    sub = ROOT / 'tests/routines/bad-routine-references/sub.b'
    message = expected_text(message_fixture)
    main = ROOT / 'tests/routines/bad-routine-references' / fixture_name
    run = subprocess.run(
        [CLI, main, sub, '-o', compiler.c], text=True, capture_output=True
    )
    assert run.returncode != 0
    assert message in run.stderr


def test_multi_unit_program_requires_package_aware_linkage(compiler):
    main = ROOT / 'tests/snippets/package-directives.b'
    routine = ROOT / 'tests/routines/show-parasentence.b'
    run = subprocess.run(
        [CLI, main, routine, '-o', compiler.c], capture_output=True, text=True
    )
    assert (run.returncode, run.stderr) == (
        1,
        expected_text(
            'multi-unit-program-requires-package-aware-linkage.stderr',
            main=main,
        ),
    )


@pytest.mark.parametrize('program', ['quine', 'quine2'])
def test_quine(compiler, program):
    source = ROOT / 'tests/programs' / f'{program}.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == source.read_bytes()


def test_seqx_resolves_as_external_function(compiler):
    source = ROOT / 'tests/routines/seqx-resolves-as-external-function/main.b'
    function = ROOT / 'tests/routines/seqx-resolves-as-external-function/seqx.b'
    result = compiler.run_native(source, function)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('seqx-resolves-as-external-function.stdout'),
        b'',
    )


def test_executable_mode(compiler):
    binary = compiler.work / 'output with spaces'
    cmd = [CLI, '--exe', ROOT / 'tests/snippets/coercion.b', '-o', binary]
    env = os.environ.copy()
    env.pop('CC', None)
    env.pop('CC_FLAGS', None)
    subprocess.run(cmd, env=env, check=True)
    expected = binary.read_bytes()
    assert (
        subprocess.check_output([binary])
        == (ROOT / 'tests/snippets/coercion.stdout').read_bytes()
    )

    wrapper = compiler.work / 'check flags.py'
    wrapper.write_text(
        "import sys\nassert '--argument with spaces' in sys.argv\nsys.exit(42)\n"
    )
    env.update(
        CC=shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper)),
        CC_FLAGS="'--argument with spaces'",
    )
    run = subprocess.run(
        [CLI, '--run', '-v', *cmd[2:]],
        env=env,
        text=True,
        capture_output=True,
    )
    assert run.returncode != 0
    command, diagnostic = run.stderr.splitlines()
    arguments = shlex.split(command)
    assert arguments[:2] == [sys.executable, str(wrapper)]
    assert '--argument with spaces' in arguments
    assert expected_text('executable-mode.stderr') in diagnostic
    assert run.stdout == ''
    assert binary.read_bytes() == expected


@pytest.mark.parametrize(
    ('keep_output', 'verbose'),
    [(True, False), (True, True), (False, True)],
)
def test_run_mode(compiler, keep_output, verbose):
    root = ROOT / 'tests/routines/exit-status'
    binary = compiler.work / 'output with spaces'
    flags = ['-v'] if verbose else []
    output = ['-o', binary.name] if keep_output else []
    env = dict(os.environ, CC='cc', CC_FLAGS='', TMPDIR=str(compiler.work))
    run = subprocess.run(
        [
            CLI,
            '--run',
            *flags,
            *output,
            root / 'main.b',
            root / 'finish.b',
        ],
        cwd=compiler.work,
        env=env,
        capture_output=True,
        timeout=10,
    )
    assert run.returncode == 23, run.stderr
    assert run.stdout == expected_bytes('exit-status-from-subroutine.stdout')
    if keep_output:
        assert binary.is_file()
    else:
        assert list(compiler.work.iterdir()) == []
    if verbose:
        compile_line, run_line = run.stderr.decode().splitlines()
        assert shlex.split(compile_line)[:2] == ['cc', '-std=c99']
        (executable,) = shlex.split(run_line)
        if keep_output:
            assert executable == str(binary)
        else:
            assert os.path.dirname(os.path.dirname(executable)) == str(
                compiler.work
            )
    else:
        assert run.stderr == b''


def test_executable_mode_links_math_with_exit_callbacks(compiler):
    source = ROOT / 'tests/programs/executable-math-and-exit.b'
    wrapper = ROOT / 'tests/io/check-math-link.py'
    binary = compiler.work / 'program'
    compiler = shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper))
    env = dict(
        os.environ, CC=compiler, CC_FLAGS='-Wall -Wextra -Werror -pedantic'
    )
    subprocess.run([CLI, '--exe', source, '-o', binary], env=env, check=True)
    run = subprocess.run([binary], capture_output=True, timeout=5, check=True)
    assert (run.stdout, run.stderr) == (
        expected_bytes('executable-mode-links-math-with-exit-callbacks.stdout'),
        b'',
    )


def test_common_scalar_dimensioned_in_routines(compiler):
    fixture = ROOT / 'tests/routines/common-scalar-dimensioned'
    fill = fixture / 'fill.linked.b'
    run = compiler.run_native(
        fixture / 'main.b', fill, fixture / 'show.linked.b'
    )
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('common-scalar-dimensioned-in-routines.stdout'),
        b'',
    )

    resize = fixture / 'resize.linked.b'
    run = compiler.run_native(fixture / 'resize.b', fill, resize)
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        b'',
        expected_text(
            'common-scalar-dimensioned-in-routines.stderr', source=resize
        ).encode(),
    )
