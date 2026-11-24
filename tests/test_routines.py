import os
import shlex
import subprocess
import sys

from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_logical_function_calls(compiler):
    main = ROOT / 'tests/routines/logical-calls/main.b'
    function = ROOT / 'tests/routines/logical-calls/bump.b'
    run = compiler.run_native(main, function)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('logical-function-calls.stdout')
    main = ROOT / 'tests/routines/logical-calls/unassigned.b'
    run = subprocess.run([CLI, main, function, '-o', compiler.c], text=True, capture_output=True)
    assert run.returncode != 0
    assert expected_text('logical-function-calls.stderr', main=main) in run.stderr


def test_conditional_expression_calls(compiler):
    main = ROOT / 'tests/routines/conditional-calls/main.b'
    function = ROOT / 'tests/routines/conditional-calls/bump.b'
    run = compiler.run_native(main, function)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (0,
             expected_bytes('conditional-expression-calls.stdout'),
             b'')
    )

    main = ROOT / 'tests/routines/conditional-calls/unassigned.b'
    run = subprocess.run([CLI, main, function, '-o', compiler.c], text=True, capture_output=True)
    assert run.returncode != 0
    assert expected_text('conditional-expression-calls.stderr', main=main) in run.stderr


def test_callonexit_dispatches_linked_callbacks(compiler, subtests):
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
        with subtests.test(ending=ending):
            source = ROOT / 'tests/routines/callonexit-dispatches-linked-callbacks' / f'exit_{case_number}.b'
            result = compiler.run_native(source, save, show, wrong)
            assert result.returncode == status, result.stderr
            assert result.stdout == expected_bytes('callonexit-dispatches-linked-callbacks.stdout')
            if ending == 'DEBUG':
                assert expected_bytes('callonexit-dispatches-linked-callbacks.stderr') in result.stderr
            else:
                assert result.stderr == b''


def test_external_subroutine(compiler):
    directory = ROOT / 'tests/routines'
    run = compiler.run_native(directory / 'caller.b', directory / 'get.status.b')
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
    caller = ROOT / 'tests/routines/call-aliases-and-expression-arguments/caller.b'
    callee = ROOT / 'tests/routines/call-aliases-and-expression-arguments/callee.b'
    run = compiler.run_native(callee, caller)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('call-aliases-and-expression-arguments.stdout')


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
    main = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/main.b'
    load = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/load.b'
    scalar = ROOT / 'tests/routines/empty-actual-uses-local-storage-for-mat-formal/scalar.b'
    result = compiler.run_native(main, load, scalar)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('empty-actual-uses-local-storage-for-mat-formal.stdout'),
             b'')
    )


def test_empty_mat_actual_requires_dimension_before_use(compiler):
    main = ROOT / 'tests/routines/empty-mat-actual-requires-dimension-before-use/main.b'
    load = ROOT / 'tests/routines/empty-mat-actual-requires-dimension-before-use/load.b'
    result = compiler.run_native(main, load)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (1,
             b'',
             expected_text('empty-mat-actual-requires-dimension-before-use.stderr', load=load).encode())
    )


def test_callc_subroutine_exists_checks_linked_subroutines(compiler):
    main = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main.b'
    subroutine = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/worker.b'
    function = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/compute.b'
    result = compiler.run_native(main, subroutine, function)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('callc-subroutine-exists-checks-linked-subroutines.stdout'),
             b'')
    )

    main = ROOT / 'tests/routines/callc-subroutine-exists-checks-linked-subroutines/main-variant-2.b'
    result = compiler.run_native(main)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('callc-subroutine-exists-checks-linked-subroutines_2.stdout'),
             b'')
    )


def test_callc_subroutine_exists_requires_two_arguments(compiler, subtests):
    for case_number, (arguments, marker, message) in enumerate((
        ("'WORKER'", ')', expected_text('callc-subroutine-exists-requires-two-arguments.stderr')),
        ("'WORKER', Info, 0", ', 0', expected_text('callc-subroutine-exists-requires-two-arguments_2.stderr')),
    ), 1):
        with subtests.test(arguments=arguments):
            statement = f'CRT CALLC JBASESubroutineExist({arguments})'
            source = ROOT / 'tests/routines/callc-subroutine-exists-requires-two-arguments' / f'main_{case_number}.b'
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('callc-subroutine-exists-requires-two-arguments_3.stderr', source=source, value_2=statement.rindex(marker) + 1, message=message)
                in result.stderr
            )


def test_call_expands_equates_in_arguments_and_indirect_targets(compiler):
    main = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/main.b'
    direct = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/direct.b'
    prefixed = ROOT / 'tests/routines/call-expands-equates-in-arguments-and-indirect-targets/prefixed.b'
    run = compiler.run_native(main, direct, prefixed)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (0,
             expected_bytes('call-expands-equates-in-arguments-and-indirect-targets.stdout'),
             b'')
    )


def test_quoted_and_punctuated_direct_routine_names(compiler):
    main = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/main.b'
    star = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/star.b'
    dashed = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/dashed.b'
    quoted_header = ROOT / 'tests/routines/quoted-and-punctuated-direct-routine-names/quoted.b'
    result = compiler.run_native(main, star, dashed, quoted_header)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('quoted-and-punctuated-direct-routine-names.stdout'),
             b'')
    )


def test_quoted_direct_target_preserves_whitespace_and_punctuation(compiler):
    main = ROOT / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main.b'
    result = subprocess.run([CLI, main, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('quoted-direct-target-preserves-whitespace-and-punctuation.stderr', main=main)
    )

    main = ROOT / 'tests/routines/quoted-direct-target-preserves-whitespace-and-punctuation/main-variant-2.b'
    result = subprocess.run([CLI, main, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('quoted-direct-target-preserves-whitespace-and-punctuation_2.stderr', main=main)
    )


def test_indirect_call_diagnostics(compiler, subtests):
    fixtures = ROOT / 'tests/routines/indirect-call-diagnostics'
    sub = fixtures / 'update.b'
    for fixture_name, name, units, message in (
            ('main_1.b', 'MISSING', (), expected_text('indirect-call-diagnostics.stderr')),
            ('main_2.b', 'update', (sub,), expected_text('indirect-call-diagnostics.stderr')),
            ('main_3.b', 'UPDATE', (sub,), expected_text('indirect-call-diagnostics_2.stderr')),
            ('main_4.b', 'UPDATE', (sub,), expected_text('indirect-call-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            main = fixtures / fixture_name
            run = compiler.run_native(main, *units)
            assert run.returncode != 0
            assert run.stdout == b''
            assert (
                expected_text('indirect-call-diagnostics_3.stderr', main=main, message=message, value_3=name).encode()
                in run.stderr
            )


def test_indirect_call_through_matrix_element(compiler):
    main = ROOT / 'tests/routines/indirect-call-through-matrix-element/main.b'
    add = ROOT / 'tests/routines/indirect-call-through-matrix-element/add.b'
    report = ROOT / 'tests/routines/indirect-call-through-matrix-element/report.b'
    change = ROOT / 'tests/routines/indirect-call-through-matrix-element/change.b'
    result = compiler.run_native(main, add, report, change)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('indirect-call-through-matrix-element.stdout'),
             b'')
    )


def test_indirect_matrix_call_uses_normal_matrix_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('main_1.b', expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics.stderr')),
        ('main_2.b', expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/indirect-matrix-call-uses-normal-matrix-diagnostics' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode == 1
            assert result.stdout == b''
            assert (
                result.stderr
                == expected_text('indirect-matrix-call-uses-normal-matrix-diagnostics_3.stderr', source=source, message=message).encode()
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
    subprocess.run([CLI, '--exe', directory / 'function.caller.b',
                    directory / 'DOUBLE.IT', '-o', binary], check=True)
    assert subprocess.check_output([binary]) == expected_bytes('external-function.stdout')


def test_deffun_call_as_statement_discards_return_and_updates_argument(compiler):
    main = ROOT / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/main.b'
    function = ROOT / 'tests/routines/deffun-call-as-statement-discards-return-and-updates-argument/function.b'
    result = compiler.run_native(main, function)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('deffun-call-as-statement-discards-return-and-updates-argument.stdout'),
             b'')
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
    for case_number, (call, formal) in enumerate([('CALL S(MAT A)', 'X'), ('CALL S(N)', 'MAT X')], 1):
        main = ROOT / 'tests/routines/matrix-parameter-diagnostics' / f'main_{case_number}.b'
        sub = ROOT / 'tests/routines/matrix-parameter-diagnostics' / f'sub_{case_number}.b'
        result = subprocess.run([CLI, main, sub, '-o', compiler.c], text=True, capture_output=True)
        assert result.returncode != 0
        assert expected_text('matrix-parameter-diagnostics.stderr', main=main) in result.stderr
    main = ROOT / 'tests/routines/matrix-parameter-diagnostics/main-variant-2.b'
    for fixture_name, message in (
        ('sub-variant-2_1.b', expected_text('matrix-parameter-diagnostics_3.stderr')),
        ('sub-variant-2_2.b', expected_text('matrix-parameter-diagnostics_4.stderr')),
        ('sub-variant-2_3.b', expected_text('matrix-parameter-diagnostics_5.stderr')),
    ):
        sub = ROOT / 'tests/routines/matrix-parameter-diagnostics' / fixture_name
        run = compiler.run_native(main, sub)
        assert run.returncode != 0
        assert expected_text('matrix-parameter-diagnostics_2.stderr', sub=sub).encode() in run.stderr
        assert message.encode() in run.stderr


def test_function_diagnostics(compiler, subtests):
    definition = ROOT / 'tests/routines/DOUBLE.IT'
    for fixture_name, message in (
        ('main_1.b', expected_text('function-diagnostics.stderr')),
        ('main_2.b', expected_text('function-diagnostics_2.stderr')),
        ('main_3.b', expected_text('function-diagnostics_3.stderr')),
        ('main_4.b', expected_text('function-diagnostics_4.stderr')),
    ):
        with subtests.test(source=fixture_name):
            main = ROOT / 'tests/routines/function-diagnostics' / fixture_name
            run = subprocess.run([CLI, main, definition, '-o', compiler.c], capture_output=True, text=True)
            assert run.returncode != 0
            assert str(main) + message in run.stderr


def test_bad_routine_references(compiler, subtests):
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
        with subtests.test(source=fixture_name):
            main = ROOT / 'tests/routines/bad-routine-references' / fixture_name
            run = subprocess.run([CLI, main, sub, '-o', compiler.c], text=True, capture_output=True)
            assert run.returncode != 0
            assert message in run.stderr


def test_multi_unit_program_requires_package_aware_linkage(compiler):
    main = ROOT / 'tests/snippets/package-directives.b'
    routine = ROOT / 'tests/routines/show-parasentence.b'
    run = subprocess.run([CLI, main, routine, '-o', compiler.c], capture_output=True, text=True)
    assert (
        (run.returncode, run.stderr)
        == (1,
             expected_text('multi-unit-program-requires-package-aware-linkage.stderr', main=main))
    )


def test_quine(compiler):
    source = ROOT / 'tests/programs/quine.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == source.read_bytes()


def test_seqx_resolves_as_external_function(compiler):
    source = ROOT / 'tests/routines/seqx-resolves-as-external-function/main.b'
    function = ROOT / 'tests/routines/seqx-resolves-as-external-function/seqx.b'
    result = compiler.run_native(source, function)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('seqx-resolves-as-external-function.stdout'),
             b'')
    )


def test_executable_mode(compiler):
    binary = compiler.work / 'output with spaces'
    cmd = [CLI, '--exe', ROOT / 'tests/snippets/coercion.b', '-o', binary]
    env = os.environ.copy()
    env.pop('CC', None)
    env.pop('CC_FLAGS', None)
    subprocess.run(cmd, env=env, check=True)
    expected = binary.read_bytes()
    assert subprocess.check_output([binary]) == (ROOT / 'tests/snippets/coercion.stdout').read_bytes()

    wrapper = compiler.work / 'check flags.py'
    wrapper.write_text("import sys\nassert '--argument with spaces' in sys.argv\nsys.exit(42)\n")
    env.update(CC=shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper)),
               CC_FLAGS="'--argument with spaces'")
    run = subprocess.run(cmd, env=env, text=True, capture_output=True)
    assert run.returncode != 0
    assert expected_text('executable-mode.stderr') in run.stderr
    assert binary.read_bytes() == expected


def test_executable_mode_links_math_with_exit_callbacks(compiler):
    source = ROOT / 'tests/programs/executable-math-and-exit.b'
    wrapper = ROOT / 'tests/io/check-math-link.py'
    binary = compiler.work / 'program'
    compiler = shlex.quote(sys.executable) + ' ' + shlex.quote(str(wrapper))
    env = dict(os.environ, CC=compiler, CC_FLAGS='-Wall -Wextra -Werror -pedantic')
    subprocess.run([CLI, '--exe', source, '-o', binary], env=env, check=True)
    run = subprocess.run([binary], capture_output=True, timeout=5, check=True)
    assert (
        (run.stdout, run.stderr)
        == (expected_bytes('executable-mode-links-math-with-exit-callbacks.stdout'),
             b'')
    )
