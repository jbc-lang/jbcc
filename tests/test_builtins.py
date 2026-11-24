import os
import re
import subprocess

from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_ins_diagnostics(compiler, subtests):
    for name, diagnostic in [
            ('ins_1.b', expected_text('ins-diagnostics.stderr')),
            ('ins_2.b', expected_text('ins-diagnostics_2.stderr')),
            ('ins_3.b', expected_text('ins-diagnostics_3.stderr'))]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert run.returncode != 0
            assert str(source) + diagnostic in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/ins-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('ins-diagnostics_4.stderr', source=source).encode() in run.stderr


def test_insert_diagnostics(compiler, subtests):
    for name, message in [
            ('insert_1.b', expected_text('insert-diagnostics.stderr')),
            ('insert_2.b', expected_text('insert-diagnostics_2.stderr'))]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert run.returncode != 0
            assert str(source) + message in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/insert-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('insert-diagnostics_3.stderr', source=source).encode() in run.stderr


def test_delete_function_rejects_nonnumeric_index(compiler):
    source = ROOT / 'tests/programs/array-diagnostics/delete-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('delete-function-rejects-nonnumeric-index.stderr', source=source).encode()
        in run.stderr
    )


def test_extract_rejects_nonnumeric_index(compiler):
    source = ROOT / 'tests/programs/array-diagnostics/extract-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('extract-rejects-nonnumeric-index.stderr', source=source).encode() in run.stderr


def test_del_diagnostics(compiler, subtests):
    for name, diagnostic in [
            ('del_1.b', expected_text('del-diagnostics.stderr')),
            ('del_2.b', expected_text('del-diagnostics_2.stderr')),
            ('del_3.b', expected_text('del-diagnostics_3.stderr'))]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert run.returncode != 0
            assert str(source) + diagnostic in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/del-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('del-diagnostics_4.stderr', source=source).encode() in run.stderr


def test_integer_limits(compiler, subtests):
    for case_number, (text, diagnostic) in enumerate([('9223372036854775807', expected_text('integer-limits.stderr')),
                             ('"nan"', expected_text('integer-limits_2.stderr'))], 1):
        with subtests.test(text=text):
            source = ROOT / 'tests/programs/integer-limits' / f'numbers_{case_number}.b'
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert diagnostic.encode() in run.stderr
            assert (
                expected_text('integer-limits_3.stderr', source=source, value_2=len(text) + 6).encode()
                in run.stderr
            )


def test_precision_call_scope(compiler):
    sources = ROOT / 'tests/routines/precision-scope'
    run = compiler.run_native(sources / 'main.b', sources / 'change.b', sources / 'local.b')
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('precision-call-scope.stdout')


def test_invalid_precision(compiler, subtests):
    for fixture_name in (
        'bad_1.b',
        'bad_2.b',
        'bad_3.b',
        'bad_4.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/invalid-precision' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert expected_text('invalid-precision.stderr', source=source).encode() in run.stderr


def test_locate_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('main_1.b', expected_text('locate-diagnostics.stderr')),
        ('main_2.b', expected_text('locate-diagnostics_2.stderr')),
        ('main_3.b', expected_text('locate-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            main = ROOT / 'tests/programs/locate-diagnostics' / fixture_name
            run = compiler.run_native(main)
            assert run.returncode != 0
            assert (
                expected_text('locate-diagnostics_4.stderr', main=main, message=message).encode()
                in run.stderr
            )


def test_locate_subvalue_start_diagnostics(compiler):
    main = ROOT / 'tests/programs/locate-zero-subvalue.b'
    run = compiler.run_native(main)
    assert run.returncode != 0
    assert expected_text('locate-subvalue-start-diagnostics.stderr', main=main).encode() in run.stderr
    main = ROOT / 'tests/programs/locate-duplicate-start.b'
    result = subprocess.run([CLI, main, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode != 0
    assert expected_text('locate-subvalue-start-diagnostics_2.stderr', main=main) in result.stderr


def test_sum_overflow_reports_call_site(compiler):
    source = ROOT / 'tests/programs/sum-overflow.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('sum-overflow-reports-call-site.stderr', source=source).encode() in run.stderr


def test_unique_key_returns_distinct_uuid_strings(compiler):
    run = compiler.run_native(ROOT / 'tests/programs/unique-key.b')
    assert (run.returncode, run.stderr) == (0, b'')
    values = run.stdout.splitlines()
    assert len(values) == 5
    assert len(set(values)) == 5
    for value in values:
        assert re.search(b'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$', value)


def test_iconv_diagnostics(compiler, subtests):
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
        with subtests.test(args=args):
            source = ROOT / 'tests/programs/iconv-diagnostics' / f'date_{case_number}.b'
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('iconv-diagnostics_5.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_iconvs_empty_mask_diagnostic(compiler):
    source = ROOT / 'tests/programs/iconvs-empty-mask.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert expected_text('iconvs-empty-mask-diagnostic.stderr', source=source).encode() in result.stderr


def test_oconvs_empty_mask_diagnostic(compiler):
    source = ROOT / 'tests/programs/oconvs-empty-mask.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert expected_text('oconvs-empty-mask-diagnostic.stderr', source=source).encode() in result.stderr


def test_oconv_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('date_1.b', expected_text('oconv-diagnostics.stderr')),
        ('date_2.b', expected_text('oconv-diagnostics_2.stderr')),
        ('date_3.b', expected_text('oconv-diagnostics_2.stderr')),
        ('date_4.b', expected_text('oconv-diagnostics_2.stderr')),
        ('date_5.b', expected_text('oconv-diagnostics_3.stderr')),
        ('date_6.b', expected_text('oconv-diagnostics_4.stderr')),
        ('date_7.b', expected_text('oconv-diagnostics_5.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/oconv-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('oconv-diagnostics_6.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_str_repetition_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('repeat_1.b', expected_text('str-repetition-diagnostics.stderr')),
        ('repeat_2.b', expected_text('str-repetition-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/str-repetition-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('str-repetition-diagnostics_3.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_spaces_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('spaces_1.b', expected_text('spaces-diagnostics.stderr')),
        ('spaces_2.b', expected_text('spaces-diagnostics.stderr')),
        ('spaces_3.b', expected_text('spaces-diagnostics.stderr')),
        ('spaces_4.b', expected_text('spaces-diagnostics.stderr')),
        ('spaces_5.b', expected_text('spaces-diagnostics_2.stderr')),
        ('spaces_6.b', expected_text('spaces-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/spaces-diagnostics' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode != 0
            assert (
                expected_text('spaces-diagnostics_4.stderr', source=source, message=message).encode()
                in result.stderr
            )


def test_left_right_require_numeric_length(compiler, subtests):
    for fixture_name in (
        'length_1.b',
        'length_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/left-right-require-numeric-length' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('left-right-require-numeric-length.stderr', source=source).encode()
                in run.stderr
            )


def test_suffix_requires_numeric_length(compiler):
    source = ROOT / 'tests/programs/suffix-nonnumeric-length.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('suffix-requires-numeric-length.stderr', source=source).encode() in run.stderr


def test_counts_requires_two_arguments(compiler, subtests):
    for fixture_name in (
        'counts_1.b',
        'counts_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/counts-requires-two-arguments' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert expected_text('counts-requires-two-arguments.stderr', source=source) in result.stderr


def test_col_positions_require_no_arguments(compiler, subtests):
    for case_number, name in enumerate(('COL1', 'COL2'), 1):
        with subtests.test(name=name):
            source = ROOT / 'tests/programs/col-positions-require-no-arguments' / f'field-positions_{case_number}.b'
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('col-positions-require-no-arguments.stderr', source=source, value_2=name)
                in result.stderr
            )


def test_delimited_bracket_assignment_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('fields_1.b', expected_text('delimited-bracket-assignment-diagnostics.stderr')),
        ('fields_2.b', expected_text('delimited-bracket-assignment-diagnostics_2.stderr')),
        ('fields_3.b', expected_text('delimited-bracket-assignment-diagnostics_3.stderr')),
        ('fields_4.b', expected_text('delimited-bracket-assignment-diagnostics_4.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/delimited-bracket-assignment-diagnostics' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode == 1
            assert result.stdout == b''
            assert (
                result.stderr
                == expected_text('delimited-bracket-assignment-diagnostics_5.stderr', source=source, message=message).encode()
            )


def test_concatenation_with_an_omitted_right_operand(compiler):
    source = ROOT / 'tests/routines/concat-omitted-operand/main.b'
    show = ROOT / 'tests/routines/concat-omitted-operand/show.b'
    result = compiler.run_native(source, show)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('concatenation-with-an-omitted-right-operand.stdout'),
             b'')
    )


def test_concatenation_requires_a_left_operand(compiler):
    source = ROOT / 'tests/programs/concat-missing-left.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode == 1
    assert result.stderr == expected_text('concatenation-requires-a-left-operand.stderr', source=source)


def test_single_index_substring_assignment_diagnostics(compiler):
    source = ROOT / 'tests/programs/substring-nonnumeric-index.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('single-index-substring-assignment-diagnostics.stderr', source=source).encode()
        in result.stderr
    )

    source = ROOT / 'tests/programs/substring-invalid-assignment.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert (
        expected_text('single-index-substring-assignment-diagnostics_2.stderr', source=source)
        in result.stderr
    )


def test_substrings_requires_numeric_bounds(compiler, subtests):
    for fixture_name in (
        'substrings_1.b',
        'substrings_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/substrings-requires-numeric-bounds' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('substrings-requires-numeric-bounds.stderr', source=source).encode()
                in run.stderr
            )


def test_splice_reuse_scalar(compiler):
    source = ROOT / 'tests/routines/splice-reuse/main.b'
    bump = ROOT / 'tests/routines/splice-reuse/bump.b'
    run = compiler.run_native(source, bump)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('splice-reuse-scalar.stdout')

    source = ROOT / 'tests/programs/splice-reuse-array.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('splice-reuse-scalar.stderr', source=source).encode() in run.stderr


def test_eqs_reuse_requires_scalar(compiler):
    source = ROOT / 'tests/programs/eqs-reuse-array.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('eqs-reuse-requires-scalar.stderr', source=source).encode() in run.stderr


def test_ordered_array_comparisons(compiler):
    source = ROOT / 'tests/routines/ordered-array-comparisons/main.b'
    bump = ROOT / 'tests/routines/ordered-array-comparisons/bump.b'
    result = compiler.run_native(source, bump)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('ordered-array-comparisons.stdout'),
             b'')
    )


def test_ordered_array_comparison_rejects_reuse_of_an_array(compiler):
    source = ROOT / 'tests/programs/les-reuse-array.b'
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == b''
    assert (
        result.stderr
        == expected_text('ordered-array-comparison-rejects-reuse-of-an-array.stderr', source=source).encode()
    )


def test_compare_invalid_justification(compiler):
    source = ROOT / 'tests/programs/compare-invalid-justification.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('compare-invalid-justification.stderr', source=source).encode() in run.stderr


def test_fold_invalid_width(compiler, subtests):
    for fixture_name in (
        'fold_1.b',
        'fold_2.b',
        'fold_3.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/fold-invalid-width' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert expected_text('fold-invalid-width.stderr', source=source).encode() in run.stderr


def test_fmts_invalid_mask(compiler, subtests):
    for fixture_name, mask in (
        ('fmts_1.b', ''),
        ('fmts_2.b', 'R?'),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/fmts-invalid-mask' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert expected_text('fmts-invalid-mask.stderr', source=source, mask=mask).encode() in run.stderr


def test_dround_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('dround_1.b', expected_text('dround-diagnostics.stderr')),
        ('dround_2.b', expected_text('dround-diagnostics_2.stderr')),
        ('dround_3.b', expected_text('dround-diagnostics_2.stderr')),
        ('dround_4.b', expected_text('dround-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/dround-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('dround-diagnostics_3.stderr', source=source, diagnostic=diagnostic).encode()
                in run.stderr
            )


def test_smul_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('smul_1.b', expected_text('smul-diagnostics.stderr')),
        ('smul_2.b', expected_text('smul-diagnostics.stderr')),
        ('smul_3.b', expected_text('smul-diagnostics_2.stderr')),
        ('smul_4.b', expected_text('smul-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/smul-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('smul-diagnostics_3.stderr', source=source, diagnostic=diagnostic).encode()
                in run.stderr
            )


def test_sdiv_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('sdiv_1.b', expected_text('sdiv-diagnostics.stderr')),
        ('sdiv_2.b', expected_text('sdiv-diagnostics.stderr')),
        ('sdiv_3.b', expected_text('sdiv-diagnostics_2.stderr')),
        ('sdiv_4.b', expected_text('sdiv-diagnostics_3.stderr')),
        ('sdiv_5.b', expected_text('sdiv-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/sdiv-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('sdiv-diagnostics_4.stderr', source=source, diagnostic=diagnostic).encode()
                in run.stderr
            )


def test_adds_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('adds_1.b', expected_text('adds-diagnostics.stderr')),
        ('adds_2.b', expected_text('adds-diagnostics_2.stderr')),
        ('adds_3.b', expected_text('adds-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/adds-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + diagnostic).encode() in run.stderr


def test_infix_reuse_requires_scalar(compiler):
    source = ROOT / 'tests/programs/infix-reuse-requires-scalar.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert expected_text('infix-reuse-requires-scalar.stderr', source=source).encode() in result.stderr


def test_muls_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('muls_1.b', expected_text('muls-diagnostics.stderr')),
        ('muls_2.b', expected_text('muls-diagnostics_2.stderr')),
        ('muls_3.b', expected_text('muls-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/muls-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + diagnostic).encode() in run.stderr


def test_divs_substitutes_zero_for_zero_divisors(compiler):
    source = ROOT / 'tests/programs/divs-substitutes-zero-for-zero-divisors.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('divs-substitutes-zero-for-zero-divisors.stdout')
    warning = expected_text('divs-substitutes-zero-for-zero-divisors.stderr', source=source)
    assert run.stderr == warning.encode() * 2


def test_infix_reuse_division_reports_invalid_operands(compiler, subtests):
    for case_number, (expression, marker, message) in enumerate((
        ("(4:@VM:6) / REUSE(0)", '/', expected_text('infix-reuse-division-reports-invalid-operands.stderr')),
        ("REUSE(8) / (2:@VM:0)", '/', expected_text('infix-reuse-division-reports-invalid-operands.stderr')),
        ("REUSE(3:@FM:4) / 2", 'REUSE', expected_text('infix-reuse-division-reports-invalid-operands_2.stderr')),
    ), 1):
        with subtests.test(expression=expression):
            statement = f'CRT {expression}'
            source = ROOT / 'tests/programs/infix-reuse-division-reports-invalid-operands' / f'reuse_{case_number}.b'
            result = compiler.run_native(source)
            assert (
                (result.returncode, result.stdout, result.stderr)
                == (1,
                     b'',
                     expected_text('infix-reuse-division-reports-invalid-operands_3.stderr', source=source, value_2=statement.index(marker) + 1, message=message).encode())
            )


def test_divs_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('divs_1.b', expected_text('divs-diagnostics.stderr')),
        ('divs_2.b', expected_text('divs-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/divs-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + diagnostic).encode() in run.stderr


def test_subs_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('subs_1.b', expected_text('subs-diagnostics.stderr')),
        ('subs_2.b', expected_text('subs-diagnostics.stderr')),
        ('subs_3.b', expected_text('subs-diagnostics_2.stderr')),
        ('subs_4.b', expected_text('subs-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/subs-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (str(source) + diagnostic).encode() in run.stderr


def test_ln_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('ln_1.b', expected_text('ln-diagnostics.stderr')),
        ('ln_2.b', expected_text('ln-diagnostics_2.stderr')),
        ('ln_3.b', expected_text('ln-diagnostics_2.stderr')),
        ('ln_4.b', expected_text('ln-diagnostics_3.stderr')),
        ('ln_5.b', expected_text('ln-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/ln-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('ln-diagnostics_4.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_exp_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('exp_1.b', expected_text('exp-diagnostics.stderr')),
        ('exp_2.b', expected_text('exp-diagnostics_2.stderr')),
        ('exp_3.b', expected_text('exp-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/exp-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('exp-diagnostics_4.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_sqrt_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('sqrt_1.b', expected_text('sqrt-diagnostics.stderr')),
        ('sqrt_2.b', expected_text('sqrt-diagnostics_2.stderr')),
        ('sqrt_3.b', expected_text('sqrt-diagnostics_3.stderr')),
        ('sqrt_4.b', expected_text('sqrt-diagnostics_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/sqrt-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('sqrt-diagnostics_4.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_power_domain_and_diagnostics(compiler, subtests):
    for fixture_name, column, message, continues in (
        ('power_1.b', 5, expected_text('power-domain-and-diagnostics.stderr'), True),
        ('power_2.b', 7, expected_text('power-domain-and-diagnostics_2.stderr'), False),
        ('power_3.b', 7, expected_text('power-domain-and-diagnostics_3.stderr'), False),
        ('power_4.b', 5, expected_text('power-domain-and-diagnostics_4.stderr'), False),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/power-domain-and-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert (run.returncode == 0) == continues
            assert run.stdout == (b'0\ndone\n' if continues else b'')
            assert (
                expected_text('power-domain-and-diagnostics_5.stderr', source=source, column=column, message=message).encode()
                in run.stderr
            )


def test_randomize_wrong_argument_count(compiler):
    source = ROOT / 'tests/programs/randomize-wrong-argument-count.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('randomize-wrong-argument-count.stderr', source=source) in result.stderr


def test_rnd_invalid_bound(compiler, subtests):
    for fixture_name, diagnostic in (
        ('rnd_1.b', expected_text('rnd-invalid-bound.stderr')),
        ('rnd_2.b', expected_text('rnd-invalid-bound.stderr')),
        ('rnd_3.b', expected_text('rnd-invalid-bound_2.stderr')),
        ('rnd_4.b', expected_text('rnd-invalid-bound_3.stderr')),
        ('rnd_5.b', expected_text('rnd-invalid-bound_3.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/rnd-invalid-bound' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('rnd-invalid-bound_4.stderr', source=source, diagnostic=diagnostic).encode()
                in run.stderr
            )


def test_bitxor_diagnostics(compiler, subtests):
    for fixture_name in (
        'bitxor_1.b',
        'bitxor_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/bitxor-diagnostics' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode != 0
            assert expected_text('bitxor-diagnostics.stderr', source=source).encode() in result.stderr

    source = ROOT / 'tests/programs/bitxor-diagnostics/bitxor-variant-2.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('bitxor-diagnostics_2.stderr', source=source) in result.stderr


def test_mod_requires_numeric_operands(compiler, subtests):
    for fixture_name, name in (
        ('mod_1.b', 'MOD'),
        ('mod_2.b', 'MOD'),
        ('mod_3.b', 'REM'),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/mod-requires-numeric-operands' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('mod-requires-numeric-operands.stderr', source=source, value_2=name).encode()
                in run.stderr
            )


def test_trim_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('trim_1.b', expected_text('trim-diagnostics.stderr')),
        ('trim_2.b', expected_text('trim-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/trim-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('trim-diagnostics_3.stderr', source=source, message=message).encode()
                in run.stderr
            )


def test_find_diagnostics(compiler):
    for fixture_name, error in (
        ('find_1.b', expected_text('find-diagnostics.stderr')),
        ('find_2.b', expected_text('find-diagnostics_2.stderr')),
        ('find_3.b', expected_text('find-diagnostics_3.stderr')),
    ):
        source = ROOT / 'tests/programs/find-diagnostics' / fixture_name
        run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
        assert run.returncode != 0
        assert expected_text('find-diagnostics_4.stderr', source=source, error=error) in run.stderr
    for case_number, keyword in enumerate(('FIND', 'FINDSTR'), 1):
        source = ROOT / 'tests/programs/find-diagnostics' / f'find-variant-2_{case_number}.b'
        run = compiler.run_native(source)
        assert run.returncode != 0
        assert (
            expected_text('find-diagnostics_5.stderr', source=source, keyword=keyword).encode()
            in run.stderr
        )


def test_swap_diagnostics(compiler):
    source = ROOT / 'tests/programs/swap-diagnostics/swap.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True)
    assert result.returncode != 0
    assert expected_text('swap-diagnostics.stderr', source=source).encode() in result.stderr
    source = ROOT / 'tests/programs/swap-diagnostics/swap-variant-2.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert expected_text('swap-diagnostics_2.stderr', source=source).encode() in result.stderr


def test_ereplace_diagnostics(compiler):
    source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True)
    assert result.returncode != 0
    assert expected_text('ereplace-diagnostics.stderr', source=source).encode() in result.stderr
    source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace-variant-2.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert expected_text('ereplace-diagnostics_2.stderr', source=source).encode() in result.stderr


def test_change_diagnostics(compiler):
    for fixture_name, error in (
        ('change_1.b', expected_text('change-diagnostics.stderr')),
        ('change_2.b', expected_text('change-diagnostics_2.stderr')),
    ):
        source = ROOT / 'tests/programs/change-diagnostics' / fixture_name
        run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
        assert run.returncode != 0
        assert expected_text('change-diagnostics_3.stderr', source=source, error=error) in run.stderr
    source = ROOT / 'tests/programs/change-diagnostics/change-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('change-diagnostics_4.stderr', source=source).encode() in run.stderr


def test_string_mutations_check_conditionally_assigned_targets(compiler, subtests):
    binary = compiler.work / 'mutate'
    for case_number, (statement, expected) in enumerate((
        ("CONVERT 'a' TO 'x' IN Value", expected_bytes('string-mutations-check-conditionally-assigned-targets.stdout')),
        ("CHANGE 'aa' TO 'x' IN Value<2>", expected_bytes('string-mutations-check-conditionally-assigned-targets_2.stdout')),
    ), 1):
        with subtests.test(statement=statement):
            source = ROOT / 'tests/programs/string-mutations-check-conditionally-assigned-targets' / f'mutate_{case_number}.b'
            subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                           env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
            found = subprocess.run([binary, 'found'], capture_output=True, timeout=5)
            assert (found.returncode, found.stdout, found.stderr) == (0, expected, b'')
            missing = subprocess.run([binary, 'missing'], capture_output=True, timeout=5)
            column = statement.index('Value') + 1
            assert (
                (missing.returncode, missing.stdout, missing.stderr)
                == (1,
                     b'',
                     expected_text('string-mutations-check-conditionally-assigned-targets.stderr', source=source, column=column).encode())
            )


def test_neg_substitutes_zero(compiler):
    source = ROOT / 'tests/programs/neg-substitutes-zero.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('neg-substitutes-zero.stdout')
    assert run.stderr == expected_text('neg-substitutes-zero.stderr', source=source).encode()


def test_negs_warns_for_nonnumeric_elements(compiler):
    source = ROOT / 'tests/programs/negs-warns-for-nonnumeric-elements.b'
    result = compiler.run_native(source)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes('negs-warns-for-nonnumeric-elements.stdout')
    warning = expected_text('negs-warns-for-nonnumeric-elements.stderr', source=source)
    assert result.stderr == warning.encode() * 2


def test_abs_diagnostics(compiler):
    source = ROOT / 'tests/programs/abs-diagnostics/abs.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('abs-diagnostics.stderr', source=source).encode() in run.stderr
    source = ROOT / 'tests/programs/abs-diagnostics/abs-variant-2.b'
    run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert run.returncode != 0
    assert expected_text('abs-diagnostics_2.stderr', source=source) in run.stderr


def test_abss_diagnostics(compiler):
    source = ROOT / 'tests/programs/abss-diagnostics.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('abss-diagnostics.stderr', source=source).encode() in run.stderr


def test_implicit_format_reports_uninitialized_mask_at_read(compiler):
    source = ROOT / 'tests/programs/implicit-format-reports-uninitialized-mask-at-read.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('implicit-format-reports-uninitialized-mask-at-read.stderr', source=source).encode()
        in run.stderr
    )


def test_fmt_diagnostics(compiler, subtests):
    for case_number, mask in enumerate(['D4/', 'R20', 'R%', "3'xx'R", 'R2,', '0T'], 1):
        with subtests.test(mask=mask):
            source = ROOT / 'tests/programs/fmt-diagnostics' / f'fmt_{case_number}.b'
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert expected_text('fmt-diagnostics.stderr', source=source, mask=mask).encode() in run.stderr


def test_index_diagnostics(compiler):
    source = ROOT / 'tests/programs/index-diagnostics/index.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode != 0
    assert expected_text('index-diagnostics.stderr', source=source) in result.stderr
    source = ROOT / 'tests/programs/index-diagnostics/index-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('index-diagnostics_2.stderr', source=source).encode() in run.stderr


def test_division_by_zero(compiler):
    source = ROOT / 'tests/programs/division-by-zero.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('division-by-zero.stderr', source=source).encode() in run.stderr


def test_div_requires_nonzero_numeric_operands(compiler, subtests):
    for fixture_name, diagnostic in (
        ('div_1.b', expected_text('div-requires-nonzero-numeric-operands.stderr')),
        ('div_2.b', expected_text('div-requires-nonzero-numeric-operands_2.stderr')),
        ('div_3.b', expected_text('div-requires-nonzero-numeric-operands_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/div-requires-nonzero-numeric-operands' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert (
                expected_text('div-requires-nonzero-numeric-operands_3.stderr', source=source, diagnostic=diagnostic).encode()
                in run.stderr
            )


def test_compound_division_by_zero(compiler):
    source = ROOT / 'tests/programs/compound-division-by-zero.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert expected_text('compound-division-by-zero.stderr', source=source).encode() in run.stderr


def test_insert_locations(compiler, subtests):
    fixtures = ROOT / 'tests/programs/insert-locations'
    source = fixtures / 'main.b'
    for variant, location in (('1', expected_text('insert-locations.stderr')), ('2', expected_text('insert-locations_2.stderr'))):
        with subtests.test(variant=variant):
            header = fixtures / variant / 'I_BROKEN'
            run = subprocess.run([CLI, '-I', header.parent, source, '-o', compiler.c],
                                 text=True, capture_output=True)
            assert run.returncode != 0
            assert str(header) + location in run.stderr
    header = fixtures / '3' / 'I_BROKEN'
    run = compiler.run_native(fixtures / 'main-variant-2.b', options=('-I', header.parent))
    assert expected_text('insert-locations_3.stderr', header=header).encode() in run.stderr


def test_remove_shared_cursor(compiler):
    caller = ROOT / 'tests/programs/remove-shared-cursor/caller.b'
    sub = ROOT / 'tests/programs/remove-shared-cursor/take.b'
    run = compiler.run_native(caller, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('remove-shared-cursor.stdout')


def test_remove_expression_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('bad_1.b', expected_text('remove-expression-diagnostics.stderr')),
        ('bad_2.b', expected_text('remove-expression-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/remove-expression-diagnostics' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert str(source) + message in result.stderr


def test_remove_checks_conditionally_assigned_source(compiler, subtests):
    binary = compiler.work / 'remove'
    fixtures = ROOT / 'tests/programs/remove-checks-conditionally-assigned-source'
    for fixture_name, column in (('statement-first.b', 19), ('expression-first.b', 16)):
        with subtests.test(source=fixture_name):
            source = fixtures / fixture_name
            subprocess.run([CLI, '--exe', source, '-o', binary], check=True,
                           env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'))
            hit = subprocess.run([binary, 'hit'], capture_output=True, timeout=5)
            assert (
                (hit.returncode, hit.stdout, hit.stderr)
                == (0,
                     expected_bytes('remove-checks-conditionally-assigned-source.stdout'),
                     b'')
            )
            miss = subprocess.run([binary, 'miss'], capture_output=True, timeout=5)
            assert (
                (miss.returncode, miss.stdout, miss.stderr)
                == (1,
                     b'',
                     expected_text('remove-checks-conditionally-assigned-source.stderr', source=source, column=column).encode())
            )


def test_matchfield_invalid_field(compiler, subtests):
    for fixture_name in (
        'matchfield_1.b',
        'matchfield_2.b',
        'matchfield_3.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/matchfield-invalid-field' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert expected_text('matchfield-invalid-field.stderr', source=source).encode() in run.stderr
