import os
import subprocess

from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_matbuild_diagnostics(compiler, subtests):
    source = ROOT / 'tests/programs/matbuild-missing-array.b'
    build = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert build.returncode != 0
    assert expected_text('matbuild-diagnostics.stderr', source=source) in build.stderr
    for fixture_name, message in (
        ('matbuild_1.b', expected_text('matbuild-diagnostics_2.stderr')),
        ('matbuild_2.b', expected_text('matbuild-diagnostics_3.stderr')),
        ('matbuild_3.b', expected_text('matbuild-diagnostics_4.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/matbuild-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('matbuild-diagnostics_5.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_matparse_diagnostics(compiler, subtests):
    source = ROOT / 'tests/programs/matparse-missing-array.b'
    build = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert build.returncode != 0
    assert expected_text('matparse-diagnostics.stderr', source=source) in build.stderr
    for fixture_name, message in (
        ('matparse_1.b', expected_text('matparse-diagnostics_2.stderr')),
        ('matparse_2.b', expected_text('matparse-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/matparse-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('matparse-diagnostics_4.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_exit_status_from_subroutine(compiler):
    main = ROOT / 'tests/routines/exit-status/main.b'
    sub = ROOT / 'tests/routines/exit-status/finish.b'
    run = compiler.run_native(main, sub)
    assert run.returncode == 23, run.stderr
    assert run.stdout == expected_bytes('exit-status-from-subroutine.stdout')
    sub = ROOT / 'tests/routines/exit-status/finish-invalid-value.b'
    run = compiler.run_native(main, sub)
    assert run.returncode != 0
    assert expected_text('exit-status-from-subroutine.stderr', sub=sub).encode() in run.stderr


def test_stop_and_abort_from_main(compiler, subtests):
    for fixture_name, status, message in (
        ('main_1.b', 0, expected_bytes('stop-and-abort-from-main.stderr')),
        ('main_2.b', 1, b''),
        ('main_3.b', 1, expected_bytes('stop-and-abort-from-main_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/stop-and-abort-from-main' / fixture_name
            run = compiler.run_native(source)
            assert (
                (run.returncode, run.stdout, run.stderr)
                == (status,
                     expected_bytes('stop-and-abort-from-main.stdout'),
                     message)
            )


def test_stop_and_abort_from_routine(compiler, subtests):
    main = ROOT / 'tests/routines/stop-and-abort/main.b'
    for fixture_name, status, message in (
        ('finish_1.b', 0, expected_bytes('stop-and-abort-from-routine.stderr')),
        ('finish_2.b', 1, expected_bytes('stop-and-abort-from-routine_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            sub = ROOT / 'tests/programs/stop-and-abort-from-routine' / fixture_name
            run = compiler.run_native(main, sub)
            assert (run.returncode, run.stdout, run.stderr) == (status, b'', message)


def test_stop_missing_message_argument(compiler):
    source = ROOT / 'tests/programs/stop-missing-message-argument.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('stop-missing-message-argument.stderr', source=source) in result.stderr


def test_mismatched_next_counter(compiler):
    source = ROOT / 'tests/programs/mismatched-next.b'
    binary = compiler.work / 'program'
    build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    assert (
        build.stderr.splitlines()
        == [expected_text('mismatched-next-counter.stderr', source=source), expected_text('mismatched-next-counter_2.stderr', source=source)]
    )
    run = subprocess.run([binary], capture_output=True, timeout=5)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('mismatched-next-counter.stdout')


def test_loop_exit_control_flow_diagnostics(compiler, subtests):
    binary = compiler.work / 'program'
    for case_number, keyword in enumerate(('EXIT', 'BREAK'), 1):
        with subtests.test(keyword=keyword):
            source = ROOT / 'tests/programs/loop-exit-control-flow-diagnostics' / f'exit_{case_number}.b'
            run = compiler.run_native(source)
            assert (
                (run.returncode, run.stdout, run.stderr)
                == (1,
                     b'',
                     expected_text('loop-exit-control-flow-diagnostics.stderr', source=source).encode())
            )
            source = ROOT / 'tests/programs/loop-exit-control-flow-diagnostics' / f'exit-variant-2_{case_number}.b'
            build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
            assert build.returncode == 0, build.stderr
            assert (
                expected_text('loop-exit-control-flow-diagnostics_2.stderr', source=source, keyword=keyword)
                in build.stderr
            )
            assert (
                subprocess.check_output([binary])
                == expected_bytes('loop-exit-control-flow-diagnostics.stdout')
            )


def test_scalar_reads_after_loop_check_earlier_iterations(compiler, subtests):
    source = ROOT / 'tests/programs/loop-scalar-read.b'
    binary = compiler.work / 'loop'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                   env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
    for limit, expected in (
        ('-1', (0, b'', b'')),
        ('0', (1, b'', expected_text('scalar-reads-after-loop-check-earlier-iterations.stderr', source=source).encode())),
        ('2', (0, expected_bytes('scalar-reads-after-loop-check-earlier-iterations.stdout'), b'')),
        ('3', (0, expected_bytes('scalar-reads-after-loop-check-earlier-iterations_2.stdout'), b'')),
    ):
        with subtests.test(limit=limit):
            run = subprocess.run([binary, limit], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_continue_outside_loop(compiler):
    source = ROOT / 'tests/programs/continue-outside-loop.b'
    binary = compiler.work / 'program'
    build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    assert expected_text('continue-outside-loop.stderr', source=source) in build.stderr
    assert subprocess.check_output([binary]) == expected_bytes('continue-outside-loop.stdout')


def test_loop_control_does_not_use_the_gosub_callers_loop(compiler):
    # The 201015.001 reference emits no jump for either statement here.
    source = ROOT / 'tests/programs/gosub-loop-control.b'
    binary = compiler.work / 'program'
    build = subprocess.run([CLI, '--exe', source, '-o', binary], capture_output=True, text=True)
    assert build.returncode == 0, build.stderr
    assert (
        build.stderr.splitlines()
        == [expected_text('loop-control-does-not-use-the-gosub-callers-loop.stderr', source=source), expected_text('loop-control-does-not-use-the-gosub-callers-loop_2.stderr', source=source)]
    )
    run = subprocess.run([binary], capture_output=True, timeout=5)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (0,
             expected_bytes('loop-control-does-not-use-the-gosub-callers-loop.stdout'),
             b'')
    )


def test_conditional_expression_requires_else(compiler):
    source = ROOT / 'tests/programs/conditional-missing-else.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('conditional-expression-requires-else.stderr', source=source) in result.stderr


def test_clear_resets_local_storage_and_preserves_shared_slots(compiler):
    main = ROOT / 'tests/routines/clear-storage/main.b'
    reset = ROOT / 'tests/routines/clear-storage/reset.b'
    result = compiler.run_native(main, reset)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('clear-resets-local-storage-and-preserves-shared-slots.stdout'),
             b'')
    )


def test_clear_requires_a_path_that_initializes_the_local(compiler):
    source = ROOT / 'tests/programs/clear-unassigned-local.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('clear-requires-a-path-that-initializes-the-local.stderr', source=source)
    )


def test_increment_and_decrement_expression_values(compiler):
    source = ROOT / 'tests/programs/increment-and-decrement-expression-values/step.b'
    routine = ROOT / 'tests/programs/increment-and-decrement-expression-values/show-steps.b'
    result = compiler.run_native(source, routine)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('increment-and-decrement-expression-values.stdout'),
             b'')
    )


def test_increment_and_decrement_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('step_1.b', expected_text('increment-and-decrement-diagnostics.stderr')),
        ('step_2.b', expected_text('increment-and-decrement-diagnostics_2.stderr')),
        ('step_3.b', expected_text('increment-and-decrement-diagnostics_3.stderr')),
        ('step_4.b', expected_text('increment-and-decrement-diagnostics_4.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/increment-and-decrement-diagnostics' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('increment-and-decrement-diagnostics_5.stderr', source=source, message=message)
                in result.stderr
            )

    source = ROOT / 'tests/programs/increment-and-decrement-diagnostics/step-variant-2.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('increment-and-decrement-diagnostics_6.stderr', source=source).encode()
        in result.stderr
    )


def test_spaced_concatenating_assignment_requires_initial_value(compiler):
    source = ROOT / 'tests/programs/spaced-concatenating-assignment-requires-initial-value.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert (
        expected_text('spaced-concatenating-assignment-requires-initial-value.stderr', source=source)
        in result.stderr
    )


def test_compound_assignment_checks_conditionally_assigned_target(compiler, subtests):
    binary = compiler.work / 'compound'
    for fixture_name, expected in (
        ('compound_1.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target.stdout')),
        ('compound_2.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target_2.stdout')),
        ('compound_3.b', expected_bytes('compound-assignment-checks-conditionally-assigned-target_3.stdout')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/compound-assignment-checks-conditionally-assigned-target' / fixture_name
            subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                           env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
            hit = subprocess.run([binary, 'hit'], capture_output=True, timeout=5)
            assert (hit.returncode, hit.stdout, hit.stderr) == (0, expected, b'')
            miss = subprocess.run([binary, 'miss'], capture_output=True, timeout=5)
            assert (
                (miss.returncode, miss.stdout, miss.stderr)
                == (1,
                     b'',
                     expected_text('compound-assignment-checks-conditionally-assigned-target.stderr', source=source).encode())
            )


def test_indexed_jump_selector(compiler):
    function = ROOT / 'tests/programs/indexed-jump-selector/pick.b'
    source = ROOT / 'tests/programs/indexed-jump-selector/dispatch.b'
    run = compiler.run_native(source, function)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('indexed-jump-selector.stdout')
    for fixture_name in (
        'dispatch-variant-2_1.b',
        'dispatch-variant-2_2.b',
    ):
        source = ROOT / 'tests/programs/indexed-jump-selector' / fixture_name
        run = compiler.run_native(source)
        assert run.returncode != 0
        assert expected_text('indexed-jump-selector.stderr', source=source).encode() in run.stderr


def test_indexed_jump_range(compiler):
    source = ROOT / 'tests/programs/indexed-jump-range.b'
    run = compiler.run_native(source)
    assert run.returncode == 0
    assert run.stdout == expected_bytes('indexed-jump-range.stdout')
    expected = [f'{source}:{line}:1: warning: ON selector out of range, using label {line}'
                for line in (1, 2)]
    assert run.stderr.decode().splitlines() == expected
    binary = compiler.work / 'pick'
    env = dict(os.environ, CC_FLAGS='-DJBCC_ON_FALLTHROUGH')
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True, env=env)
    run = subprocess.run([binary], capture_output=True)
    assert run.returncode == 0
    assert run.stdout == expected_bytes('indexed-jump-range_2.stdout')
    assert run.stderr == b''


def test_jump_discards_step_when_reentering_a_completed_for(compiler):
    source = ROOT / 'tests/programs/jump-discards-step-when-reentering-a-completed-for.b'
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == expected_bytes('jump-discards-step-when-reentering-a-completed-for.stdout')
    assert (
        result.stderr
        == expected_text('jump-discards-step-when-reentering-a-completed-for.stderr', source=source).encode()
    )


def test_next_after_jump_requires_assigned_counter(compiler):
    source = ROOT / 'tests/programs/next-after-jump-requires-assigned-counter.b'
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == expected_bytes('next-after-jump-requires-assigned-counter.stdout')
    assert (
        result.stderr
        == expected_text('next-after-jump-requires-assigned-counter.stderr', source=source).encode()
    )


def test_return_to_unwinds_subroutine(compiler):
    main = ROOT / 'tests/programs/return-to-unwinds-subroutine/main.b'
    sub = ROOT / 'tests/programs/return-to-unwinds-subroutine/sub.b'
    run = compiler.run_native(main, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('return-to-unwinds-subroutine.stdout')


def test_return_to_without_caller(compiler):
    main = ROOT / 'tests/programs/return-to-without-caller.b'
    run = compiler.run_native(main)
    assert run.returncode != 0
    assert expected_text('return-to-without-caller.stderr', main=main).encode() in run.stderr


def test_return_to_bypasses_for_header_with_explicit_step(compiler):
    main = ROOT / 'tests/programs/return-to-bypasses-for-header-with-explicit-step.b'
    run = compiler.run_native(main)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (1,
             expected_bytes('return-to-bypasses-for-header-with-explicit-step.stdout'),
             expected_text('return-to-bypasses-for-header-with-explicit-step.stderr', main=main).encode())
    )


def test_deferred_scalar_read_warns_and_fails_only_when_reached(compiler, subtests):
    source = ROOT / 'tests/programs/deferred-scalar-read-warns-and-fails-only-when-reached.b'
    binary = compiler.work / 'program'
    command = [CLI, '--exe', source, '-o', binary]
    strict = subprocess.run(command, capture_output=True, text=True)
    assert strict.returncode == 1
    assert (
        strict.stderr
        == expected_text('deferred-scalar-read-warns-and-fails-only-when-reached.stderr', source=source)
    )
    deferred = subprocess.run([*command, '--defer-unassigned-reads'], capture_output=True, text=True, check=True)
    assert (
        deferred.stderr
        == expected_text('deferred-scalar-read-warns-and-fails-only-when-reached_2.stderr', source=source)
    )
    for flag, expected in (
        ('0', (0, expected_bytes('deferred-scalar-read-warns-and-fails-only-when-reached.stdout'), b'')),
        ('1', (1, b'', expected_text('deferred-scalar-read-warns-and-fails-only-when-reached_3.stderr', source=source).encode())),
    ):
        with subtests.test(flag=flag):
            run = subprocess.run([binary], capture_output=True, timeout=5,
                                 env=dict(os.environ, JBCC_TEST_DEFERRED_READ=flag))
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_deferred_compound_assignment_checks_previous_value_when_reached(compiler, subtests):
    source = ROOT / 'tests/programs/deferred-compound-assignment.b'
    binary = compiler.work / 'program'
    command = [CLI, '--exe', source, '-o', binary]
    strict = subprocess.run(command, capture_output=True, text=True)
    assert (
        (strict.returncode, strict.stderr)
        == (1,
             expected_text('deferred-compound-assignment-checks-previous-value-when-reached.stderr', source=source))
    )
    deferred = subprocess.run([*command, '--defer-unassigned-reads'], capture_output=True, text=True, check=True)
    assert (
        deferred.stderr.splitlines()
        == [expected_text('deferred-compound-assignment-checks-previous-value-when-reached_2.stderr', source=source), expected_text('deferred-compound-assignment-checks-previous-value-when-reached_3.stderr', source=source)]
    )
    for mode, expected in (
        ('skip', (0, expected_bytes('deferred-compound-assignment-checks-previous-value-when-reached.stdout'), b'')),
        ('add', (1, b'', expected_text('deferred-compound-assignment-checks-previous-value-when-reached.stderr', source=source).encode())),
        ('append', (1, b'', expected_text('deferred-compound-assignment-checks-previous-value-when-reached_4.stderr', source=source).encode())),
    ):
        with subtests.test(mode=mode):
            run = subprocess.run([binary, mode], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_deferred_reads_still_reject_unknown_functions(compiler):
    source = ROOT / 'tests/programs/deferred-reads-still-reject-unknown-functions.b'
    result = subprocess.run([CLI, '--defer-unassigned-reads', source, '-o', compiler.c],
                            capture_output=True, text=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('deferred-reads-still-reject-unknown-functions.stderr', source=source)
    )


def test_common_storage(compiler):
    caller = ROOT / 'tests/routines/common-storage/caller.b'
    sub = ROOT / 'tests/routines/common-storage/sub.b'
    run = compiler.run_native(caller, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('common-storage.stdout')
    sub = ROOT / 'tests/routines/common-storage/sub-variant-2.b'
    result = subprocess.run([CLI, caller, sub, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('common-storage.stderr') in result.stderr


def test_conflicting_common_declarations(compiler, subtests):
    for fixture_name in (
        'conflict_1.b',
        'conflict_2.b',
        'conflict_3.b',
        'conflict_4.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/conflicting-common-declarations' / fixture_name
            run = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert run.returncode != 0
            assert expected_text('conflicting-common-declarations.stderr', source=source) in run.stderr


def test_common_member_keeps_first_slot_when_dimensioned_later(compiler):
    main = ROOT / 'tests/routines/common-member-keeps-first-slot-when-dimensioned-later/main.b'
    sub = ROOT / 'tests/routines/common-member-keeps-first-slot-when-dimensioned-later/update.b'
    result = compiler.run_native(main, sub)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('common-member-keeps-first-slot-when-dimensioned-later.stdout'),
             b'')
    )


def test_repeated_include_reuses_common_matrix_slots(compiler):
    main = ROOT / 'tests/routines/repeated-include-reuses-common-matrix-slots/main.b'
    sub = ROOT / 'tests/routines/repeated-include-reuses-common-matrix-slots/check.b'
    result = compiler.run_native(main, sub)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('repeated-include-reuses-common-matrix-slots.stdout')
    assert result.stderr == b''


def test_repeated_common_matrix_rejects_incompatible_dimensions(compiler, subtests):
    source = ROOT / 'tests/routines/repeated-common-matrix-rejects-incompatible-dimensions/bad.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True)
    assert result.returncode != 0
    assert (
        expected_text('repeated-common-matrix-rejects-incompatible-dimensions.stderr', source=source).encode()
        in result.stderr
    )

    for fixture_name in (
        'bad-variant-2_1.b',
        'bad-variant-2_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/repeated-common-matrix-rejects-incompatible-dimensions' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode != 0
            assert (
                expected_text('repeated-common-matrix-rejects-incompatible-dimensions_2.stderr', source=source).encode()
                in result.stderr
            )


def test_dim_reuses_named_and_unnamed_common_matrix_slots(compiler):
    main = ROOT / 'tests/routines/dim-reuses-named-and-unnamed-common-matrix-slots/main.b'
    sub = ROOT / 'tests/routines/dim-reuses-named-and-unnamed-common-matrix-slots/update.b'
    result = compiler.run_native(main, sub)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('dim-reuses-named-and-unnamed-common-matrix-slots.stdout')
    assert result.stderr == b''


def test_dim_rejects_a_common_matrix_rank_change(compiler):
    source = ROOT / 'tests/routines/dim-rejects-a-common-matrix-rank-change.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stderr == expected_text('dim-rejects-a-common-matrix-rank-change.stderr', source=source)


def test_common_matrix_subscript_mismatches_report_when_reached(compiler, subtests):
    for fixture_name in (
        'subscripts_1.b',
        'subscripts_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/common-matrix-subscript-mismatches-report-when-reached' / fixture_name
            result = compiler.run_native(source)
            assert (
                (result.returncode, result.stdout)
                == (1,
                     expected_bytes('common-matrix-subscript-mismatches-report-when-reached.stdout'))
            )
            assert (
                result.stderr
                == expected_text('common-matrix-subscript-mismatches-report-when-reached.stderr', source=source).encode()
            )


def test_dim_reports_a_reached_common_matrix_resize(compiler, subtests):
    for fixture_name in (
        'shape_1.b',
        'shape_2.b',
        'shape_3.b',
        'shape_4.b',
        'shape_5.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/dim-reports-a-reached-common-matrix-resize' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode == 1, result.stderr
            assert result.stdout == b''
            assert (
                result.stderr
                == expected_text('dim-reports-a-reached-common-matrix-resize.stderr', source=source).encode()
            )


def test_runtime_common_dimensions(compiler):
    main = ROOT / 'tests/routines/runtime-common-dimensions/main.b'
    sub = ROOT / 'tests/routines/runtime-common-dimensions/change.b'
    run = compiler.run_native(main, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('runtime-common-dimensions.stdout')


def test_local_dimensions_per_invocation(compiler):
    main = ROOT / 'tests/routines/local-dimensions-per-invocation/main.b'
    routine = ROOT / 'tests/routines/local-dimensions-per-invocation/nested.b'
    bump = ROOT / 'tests/routines/local-dimensions-per-invocation/bump.b'
    run = compiler.run_native(main, routine, bump)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('local-dimensions-per-invocation.stdout')


def test_forward_matrix_declarations_follow_execution_order(compiler):
    main = ROOT / 'tests/routines/forward-matrix-declarations-follow-execution-order/main.b'
    routine = ROOT / 'tests/routines/forward-matrix-declarations-follow-execution-order/check.b'
    result = compiler.run_native(main, routine)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('forward-matrix-declarations-follow-execution-order.stdout'),
             b'')
    )


def test_scalar_can_be_used_before_a_later_local_dim(compiler):
    main = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/main.b'
    routine = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/append.b'
    result = compiler.run_native(main, routine)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('scalar-can-be-used-before-a-later-local-dim.stdout'),
             b'')
    )

    main = ROOT / 'tests/routines/scalar-can-be-used-before-a-later-local-dim/main-variant-2.b'
    result = subprocess.run([CLI, main, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('scalar-can-be-used-before-a-later-local-dim.stderr', main=main) in result.stderr


def test_forward_matrix_errors_use_reference_location(compiler):
    source = ROOT / 'tests/routines/forward-matrix-errors-use-reference-location/forward.b'
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('forward-matrix-errors-use-reference-location.stderr', source=source).encode()
    )

    source = ROOT / 'tests/routines/forward-matrix-errors-use-reference-location/forward-variant-2.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('forward-matrix-errors-use-reference-location_2.stderr', source=source)
    )


def test_repeated_local_dim_reuses_storage_from_either_path(compiler):
    caller = ROOT / 'tests/routines/repeated-local-dim-reuses-storage-from-either-path/main.b'
    routine = ROOT / 'tests/routines/repeated-local-dim-reuses-storage-from-either-path/store.b'
    result = compiler.run_native(caller, routine)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('repeated-local-dim-reuses-storage-from-either-path.stdout')
    assert result.stderr == b''


def test_repeated_local_dim_rejects_changed_rank(compiler):
    source = ROOT / 'tests/routines/repeated-local-dim-rejects-changed-rank.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stderr == expected_text('repeated-local-dim-rejects-changed-rank.stderr', source=source)


def test_repeated_local_dim_reports_reached_resize(compiler, subtests):
    for fixture_name in (
        'shape_1.b',
        'shape_2.b',
        'shape_3.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/routines/repeated-local-dim-reports-reached-resize' / fixture_name
            result = compiler.run_native(source)
            assert (
                (result.returncode, result.stdout)
                == (1,
                     expected_bytes('repeated-local-dim-reports-reached-resize.stdout'))
            )
            assert (
                result.stderr
                == expected_text('repeated-local-dim-reports-reached-resize.stderr', source=source).encode()
            )


def test_local_dimension_errors(compiler, subtests):
    cases = [
        ("N = 1.5\nDIM A(N)", expected_text('local-dimension-errors.stderr')),
        ("N = 50000\nDIM A(N,N)", expected_text('local-dimension-errors_2.stderr')),
        ("N = 2\nIF 0 THEN DIM A(N)\nMAT A = 0", expected_text('local-dimension-errors_3.stderr')),
        ("FOR N = 1 TO 2\nDIM A(N)\nNEXT", expected_text('local-dimension-errors_4.stderr')),
        ("N = 2\nDIM A(N)\nN = 3\nA(N) = 1", expected_text('local-dimension-errors_5.stderr')),
    ]
    for case_number, (program, location) in enumerate(cases, 1):
        with subtests.test(program=program):
            source = ROOT / 'tests/routines/local-dimension-errors' / f'bad_{case_number}.b'
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + location).encode() in run.stderr


def test_runtime_common_dimension_errors(compiler, subtests):
    cases = [
        ("N = 1.5\nCOMMON A(N)", expected_text('runtime-common-dimension-errors.stderr')),
        ("N = 50000\nCOMMON A(N,N)", expected_text('runtime-common-dimension-errors_2.stderr')),
        ("N = 2\nIF 0 THEN COMMON A(N)\nMAT A = 0", expected_text('runtime-common-dimension-errors_3.stderr')),
        ("FOR N = 1 TO 2\nCOMMON A(N)\nNEXT", expected_text('runtime-common-dimension-errors_4.stderr')),
    ]
    for case_number, (program, location) in enumerate(cases, 1):
        with subtests.test(program=program):
            source = ROOT / 'tests/routines/runtime-common-dimension-errors' / f'bad_{case_number}.b'
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + location).encode() in run.stderr


def test_common_runtime_shape_across_routines(compiler):
    main = ROOT / 'tests/routines/common-runtime-shape-across-routines/main.b'
    sub = ROOT / 'tests/routines/common-runtime-shape-across-routines/sub.b'
    run = compiler.run_native(main, sub)
    assert run.returncode != 0
    assert expected_text('common-runtime-shape-across-routines.stderr', sub=sub).encode() in run.stderr


def test_assignment_predicates_on_arguments(compiler):
    caller = ROOT / 'tests/programs/assignment-predicates-on-arguments/caller.b'
    sub = ROOT / 'tests/programs/assignment-predicates-on-arguments/init.b'
    run = compiler.run_native(caller, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('assignment-predicates-on-arguments.stdout')


def test_expression_reads_after_conditional_assignment_are_checked_at_runtime(compiler, subtests):
    binary = compiler.work / 'guard'
    source = ROOT / 'tests/programs/expression-reads-after-conditional-assignment-are-checked-at-runtime.b'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                   env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
    for argument, expected in (
        ('hit', (0, expected_bytes('expression-reads-after-conditional-assignment-are-checked-at-runtime.stdout'), b'')),
        ('skip', (0, expected_bytes('expression-reads-after-conditional-assignment-are-checked-at-runtime_2.stdout'), b'')),
        ('broken', (1, b'', expected_text('expression-reads-after-conditional-assignment-are-checked-at-runtime.stderr', source=source).encode())),
    ):
        with subtests.test(argument=argument):
            run = subprocess.run([binary, argument], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_scalar_reads_after_case_are_checked_at_runtime(compiler, subtests):
    binary = compiler.work / 'case'
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
        with subtests.test(argument=argument):
            run = subprocess.run([binary, argument], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_case_assignment_diagnostics_exclude_unreachable_and_sibling_arms(compiler, subtests):
    for fixture_name, location in (
        ('case_1.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms.stderr')),
        ('case_2.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_2.stderr')),
        ('case_3.b', expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/case-assignment-diagnostics-exclude-unreachable-and-sibling-arms' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('case-assignment-diagnostics-exclude-unreachable-and-sibling-arms_4.stderr', source=source, location=location)
                in result.stderr
            )


def test_scalar_reads_after_for_are_checked_at_runtime(compiler, subtests):
    binary = compiler.work / 'for-loop'
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
        with subtests.test(bound=bound):
            run = subprocess.run([binary, bound], capture_output=True, timeout=5)
            assert (run.returncode, run.stdout, run.stderr) == expected


def test_for_reads_check_values_from_earlier_iterations(compiler, subtests):
    binary = compiler.work / 'iteration'
    for case_number, branch in enumerate((
        "IF I = 1 THEN Value = 'first' ELSE Value := ':' : I",
        "IF I # 1 THEN Value := ':' : I ELSE Value = 'first'",
    ), 1):
        with subtests.test(branch=branch):
            source = ROOT / 'tests/programs/for-reads-check-values-from-earlier-iterations' / f'iteration_{case_number}.b'
            subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                           env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
            hit = subprocess.run([binary, '1'], capture_output=True, timeout=5)
            assert (
                (hit.returncode, hit.stdout, hit.stderr)
                == (0,
                     expected_bytes('for-reads-check-values-from-earlier-iterations.stdout'),
                     b'')
            )
            miss = subprocess.run([binary, '2'], capture_output=True, timeout=5)
            column = branch.index('Value :=') + 1
            assert (
                (miss.returncode, miss.stdout, miss.stderr)
                == (1,
                     b'',
                     expected_text('for-reads-check-values-from-earlier-iterations.stderr', source=source, column=column).encode())
            )


def test_for_reads_without_an_initializer_are_compile_errors(compiler, subtests):
    for fixture_name, column in (
        ('iteration_1.b', 5),
        ('iteration_2.b', 1),
        ('iteration_3.b', 9),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/for-reads-without-an-initializer-are-compile-errors' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('for-reads-without-an-initializer-are-compile-errors.stderr', source=source, column=column)
                in result.stderr
            )
            assert (
                expected_text('for-reads-without-an-initializer-are-compile-errors_2.stderr')
                in result.stderr
            )


def test_assignment_probe_does_not_initialize(compiler, subtests):
    for fixture_name, location in (
        ('probe_1.b', expected_text('assignment-probe-does-not-initialize.stderr')),
        ('probe_2.b', expected_text('assignment-probe-does-not-initialize_2.stderr')),
        ('probe_3.b', expected_text('assignment-probe-does-not-initialize_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/assignment-probe-does-not-initialize' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert str(source) + location in result.stderr


def test_matrix_assignment_diagnostics(compiler):
    source = ROOT / 'tests/routines/matrix-assignment-diagnostics/main.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('matrix-assignment-diagnostics.stderr', source=source).encode() in run.stderr
    source = ROOT / 'tests/routines/matrix-assignment-diagnostics/main-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('matrix-assignment-diagnostics_2.stderr', source=source).encode() in run.stderr


def test_matrix_fill_evaluates_expression_once(compiler):
    source = ROOT / 'tests/routines/matrix-fill-evaluates-expression-once/main.b'
    function = ROOT / 'tests/routines/matrix-fill-evaluates-expression-once/BUMP'
    run = compiler.run_native(source, function)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('matrix-fill-evaluates-expression-once.stdout')


def test_matrix_element_argument_and_bounds(compiler):
    main = ROOT / 'tests/routines/matrix-element-argument-and-bounds/main.b'
    callee = ROOT / 'tests/routines/matrix-element-argument-and-bounds/put.b'
    run = compiler.run_native(main, callee)
    assert run.stdout == expected_bytes('matrix-element-argument-and-bounds.stdout')
    main = ROOT / 'tests/routines/matrix-element-argument-and-bounds/main-variant-2.b'
    run = compiler.run_native(main)
    assert run.returncode != 0
    assert expected_text('matrix-element-argument-and-bounds.stderr', main=main).encode() in run.stderr
