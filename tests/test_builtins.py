import os
import re
import subprocess

import pytest
from compiler_support import (
    CLI,
    ROOT,
    assert_unassigned_warning,
    expected_bytes,
    expected_text,
)


def test_ins_diagnostics(compiler, subtests):
    for name, diagnostic in [
        ('ins_1.b', expected_text('ins-diagnostics.stderr')),
        ('ins_2.b', expected_text('ins-diagnostics_2.stderr')),
        ('ins_3.b', expected_text('ins-diagnostics_3.stderr')),
    ]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run(
                [CLI, source, '-o', compiler.c], capture_output=True, text=True
            )
            assert run.returncode != 0
            assert str(source) + diagnostic in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/ins-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('ins-diagnostics_4.stderr', source=source).encode()
        in run.stderr
    )


def test_insert_diagnostics(compiler, subtests):
    for name, message in [
        ('insert_1.b', expected_text('insert-diagnostics.stderr')),
        ('insert_2.b', expected_text('insert-diagnostics_2.stderr')),
    ]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run(
                [CLI, source, '-o', compiler.c], capture_output=True, text=True
            )
            assert run.returncode != 0
            assert str(source) + message in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/insert-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('insert-diagnostics_3.stderr', source=source).encode()
        in run.stderr
    )


def test_delete_function_rejects_nonnumeric_index(compiler):
    source = ROOT / 'tests/programs/array-diagnostics/delete-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'delete-function-rejects-nonnumeric-index.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_extract_rejects_nonnumeric_index(compiler):
    source = (
        ROOT / 'tests/programs/array-diagnostics/extract-nonnumeric-index.b'
    )
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'extract-rejects-nonnumeric-index.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_del_diagnostics(compiler, subtests):
    for name, diagnostic in [
        ('del_1.b', expected_text('del-diagnostics.stderr')),
        ('del_2.b', expected_text('del-diagnostics_2.stderr')),
        ('del_3.b', expected_text('del-diagnostics_3.stderr')),
    ]:
        with subtests.test(source=name):
            source = ROOT / 'tests/programs/array-diagnostics' / name
            run = subprocess.run(
                [CLI, source, '-o', compiler.c], capture_output=True, text=True
            )
            assert run.returncode != 0
            assert str(source) + diagnostic in run.stderr
    source = ROOT / 'tests/programs/array-diagnostics/del-nonnumeric-index.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('del-diagnostics_4.stderr', source=source).encode()
        in run.stderr
    )


def test_precision_call_scope(compiler):
    sources = ROOT / 'tests/routines/precision-scope'
    run = compiler.run_native(
        sources / 'main.b', sources / 'change.b', sources / 'local.b'
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('precision-call-scope.stdout')


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('bad_1.b', id='bad-1'),
        pytest.param('bad_2.b', id='bad-2'),
        pytest.param('bad_3.b', id='bad-3'),
        pytest.param('bad_4.b', id='bad-4'),
    ],
)
def test_invalid_precision(compiler, fixture_name):
    source = ROOT / 'tests/programs/invalid-precision' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('invalid-precision.stderr', source=source).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('main_1.b', 'locate-diagnostics.stderr', id='main-1'),
        pytest.param('main_2.b', 'locate-diagnostics_2.stderr', id='main-2'),
        pytest.param('main_3.b', 'locate-diagnostics_3.stderr', id='main-3'),
    ],
)
def test_locate_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    main = ROOT / 'tests/programs/locate-diagnostics' / fixture_name
    run = compiler.run_native(main)
    assert run.returncode != 0
    assert (
        expected_text(
            'locate-diagnostics_4.stderr', main=main, message=message
        ).encode()
        in run.stderr
    )


def test_locate_subvalue_start_diagnostics(compiler):
    # TAFC drops a trailing zero coordinate, so <1,1,0> searches as <1,1>
    # (observed reference run, tests/tafc/locate-forms-*.b).
    main = ROOT / 'tests/programs/locate-zero-subvalue.b'
    for emulation in ('prime', 'jbase'):
        run = compiler.run_native(main, options=['--emulation', emulation])
        assert run.returncode == 0, run.stderr
    # Prime ignores a separate start after coordinates; jbase has two.
    main = ROOT / 'tests/programs/locate-duplicate-start.b'
    result = subprocess.run(
        [CLI, '--emulation', 'jbase', main, '-o', compiler.c],
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert (
        expected_text('locate-subvalue-start-diagnostics_2.stderr', main=main)
        in result.stderr
    )


def test_unique_key_returns_distinct_uuid_strings(compiler):
    run = compiler.run_native(ROOT / 'tests/programs/unique-key.b')
    assert (run.returncode, run.stderr) == (0, b'')
    values = run.stdout.splitlines()
    assert len(values) == 5
    assert len(set(values)) == 5
    for value in values:
        assert re.search(
            b'^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$',
            value,
        )


def test_iconvs_empty_mask_diagnostic(compiler):
    source = ROOT / 'tests/programs/iconvs-empty-mask.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'iconvs-empty-mask-diagnostic.stderr', source=source
        ).encode()
        in result.stderr
    )


def test_oconvs_empty_mask_diagnostic(compiler):
    source = ROOT / 'tests/programs/oconvs-empty-mask.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'oconvs-empty-mask-diagnostic.stderr', source=source
        ).encode()
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('date_7.b', 'oconv-diagnostics_5.stderr', id='date-7'),
    ],
)
def test_oconv_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/oconv-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'oconv-diagnostics_6.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'repeat_1.b', 'str-repetition-diagnostics.stderr', id='repeat-1'
        ),
        pytest.param(
            'repeat_2.b', 'str-repetition-diagnostics_2.stderr', id='repeat-2'
        ),
    ],
)
def test_str_repetition_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/str-repetition-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'str-repetition-diagnostics_3.stderr',
            source=source,
            message=message,
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('spaces_1.b', 'spaces-diagnostics.stderr', id='spaces-1'),
        pytest.param('spaces_2.b', 'spaces-diagnostics.stderr', id='spaces-2'),
        pytest.param('spaces_3.b', 'spaces-diagnostics.stderr', id='spaces-3'),
        pytest.param('spaces_4.b', 'spaces-diagnostics.stderr', id='spaces-4'),
        pytest.param(
            'spaces_5.b', 'spaces-diagnostics_2.stderr', id='spaces-5'
        ),
        pytest.param(
            'spaces_6.b', 'spaces-diagnostics_3.stderr', id='spaces-6'
        ),
    ],
)
def test_spaces_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/spaces-diagnostics' / fixture_name
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'spaces-diagnostics_4.stderr', source=source, message=message
        ).encode()
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('length_1.b', id='length-1'),
        pytest.param('length_2.b', id='length-2'),
    ],
)
def test_left_right_require_numeric_length(compiler, fixture_name):
    source = (
        ROOT / 'tests/programs/left-right-require-numeric-length' / fixture_name
    )
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'left-right-require-numeric-length.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_suffix_requires_numeric_length(compiler):
    source = ROOT / 'tests/programs/suffix-nonnumeric-length.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'suffix-requires-numeric-length.stderr', source=source
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('counts_1.b', id='counts-1'),
        pytest.param('counts_2.b', id='counts-2'),
    ],
)
def test_counts_requires_two_arguments(compiler, fixture_name):
    source = (
        ROOT / 'tests/programs/counts-requires-two-arguments' / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('counts-requires-two-arguments.stderr', source=source)
        in result.stderr
    )


@pytest.mark.parametrize(
    'case_number, name',
    [
        pytest.param(1, 'COL1', id='col1'),
        pytest.param(2, 'COL2', id='col2'),
    ],
)
def test_col_positions_require_no_arguments(compiler, case_number, name):
    source = (
        ROOT
        / 'tests/programs/col-positions-require-no-arguments'
        / f'field-positions_{case_number}.b'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'col-positions-require-no-arguments.stderr',
            source=source,
            value_2=name,
        )
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'fields_2.b',
            'delimited-bracket-assignment-diagnostics_2.stderr',
            id='fields-2',
        ),
        pytest.param(
            'fields_3.b',
            'delimited-bracket-assignment-diagnostics_3.stderr',
            id='fields-3',
        ),
        pytest.param(
            'fields_4.b',
            'delimited-bracket-assignment-diagnostics_4.stderr',
            id='fields-4',
        ),
    ],
)
def test_delimited_bracket_assignment_diagnostics(
    compiler, fixture_name, message_fixture
):
    message = expected_text(message_fixture)
    source = (
        ROOT
        / 'tests/programs/delimited-bracket-assignment-diagnostics'
        / fixture_name
    )
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == b''
    assert (
        result.stderr
        == expected_text(
            'delimited-bracket-assignment-diagnostics_5.stderr',
            source=source,
            message=message,
        ).encode()
    )


def test_concatenation_with_an_omitted_right_operand(compiler):
    source = ROOT / 'tests/routines/concat-omitted-operand/main.b'
    show = ROOT / 'tests/routines/concat-omitted-operand/show.b'
    result = compiler.run_native(source, show)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('concatenation-with-an-omitted-right-operand.stdout'),
        b'',
    )


def test_concatenation_requires_a_left_operand(compiler):
    source = ROOT / 'tests/programs/concat-missing-left.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'concatenation-requires-a-left-operand.stderr', source=source
    )


def test_single_index_substring_assignment_diagnostics(compiler):
    source = ROOT / 'tests/programs/substring-nonnumeric-index.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text(
            'single-index-substring-assignment-diagnostics.stderr',
            source=source,
        ).encode()
        in result.stderr
    )

    source = ROOT / 'tests/programs/substring-invalid-assignment.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'single-index-substring-assignment-diagnostics_2.stderr',
            source=source,
        )
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('substrings_1.b', id='substrings-1'),
        pytest.param('substrings_2.b', id='substrings-2'),
    ],
)
def test_substrings_requires_numeric_bounds(compiler, fixture_name):
    source = (
        ROOT
        / 'tests/programs/substrings-requires-numeric-bounds'
        / fixture_name
    )
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'substrings-requires-numeric-bounds.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_ordered_array_comparisons(compiler):
    source = ROOT / 'tests/routines/ordered-array-comparisons/main.b'
    bump = ROOT / 'tests/routines/ordered-array-comparisons/bump.b'
    result = compiler.run_native(source, bump)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('ordered-array-comparisons.stdout'),
        b'',
    )


def test_compare_invalid_justification(compiler):
    source = ROOT / 'tests/programs/compare-invalid-justification.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'compare-invalid-justification.stderr', source=source
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('fold_1.b', id='fold-1'),
        pytest.param('fold_2.b', id='fold-2'),
        pytest.param('fold_3.b', id='fold-3'),
    ],
)
def test_fold_invalid_width(compiler, fixture_name):
    source = ROOT / 'tests/programs/fold-invalid-width' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('fold-invalid-width.stderr', source=source).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, mask',
    [
        pytest.param('fmts_2.b', 'R?', id='fmts-2'),
    ],
)
def test_fmts_invalid_mask(compiler, fixture_name, mask):
    source = ROOT / 'tests/programs/fmts-invalid-mask' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'fmts-invalid-mask.stderr', source=source, mask=mask
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('dround_1.b', 'dround-diagnostics.stderr', id='dround-1'),
        pytest.param(
            'dround_2.b', 'dround-diagnostics_2.stderr', id='dround-2'
        ),
        pytest.param(
            'dround_3.b', 'dround-diagnostics_2.stderr', id='dround-3'
        ),
        pytest.param(
            'dround_4.b', 'dround-diagnostics_2.stderr', id='dround-4'
        ),
    ],
)
def test_dround_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/programs/dround-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'dround-diagnostics_3.stderr', source=source, diagnostic=diagnostic
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('smul_3.b', 'smul-diagnostics_2.stderr', id='smul-3'),
        pytest.param('smul_4.b', 'smul-diagnostics_2.stderr', id='smul-4'),
    ],
)
def test_smul_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/programs/smul-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'smul-diagnostics_3.stderr', source=source, diagnostic=diagnostic
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('sdiv_2.b', 'sdiv-diagnostics_2.stderr', id='sdiv-2'),
        pytest.param('sdiv_3.b', 'sdiv-diagnostics_2.stderr', id='sdiv-3'),
        pytest.param('sdiv_4.b', 'sdiv-diagnostics_3.stderr', id='sdiv-4'),
        pytest.param('sdiv_5.b', 'sdiv-diagnostics_3.stderr', id='sdiv-5'),
    ],
)
def test_sdiv_diagnostics(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/programs/sdiv-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'sdiv-diagnostics_4.stderr', source=source, diagnostic=diagnostic
        ).encode()
        in run.stderr
    )


def test_string_math_nonnumeric_operands_warn(compiler):
    """TAFC PB201214 reads a nonnumeric SADD, SSUB, SMUL or SDIV operand as
    0 and goes on (tests/tafc/string-math.b)."""
    source = compiler.work / 'string-math-nonnumeric.b'
    source.write_text(
        "CRT SADD('x', 1):' ':SSUB(2, 'y'):' ':SMUL('text', 2):' ':SDIV('', 2)\n"
    )
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == b'1 2 0 0\n'
    assert run.stderr.count(b'warning: Non-numeric value -- ZERO USED') == 3


def test_divs_substitutes_zero_for_zero_divisors(compiler):
    source = ROOT / 'tests/programs/divs-substitutes-zero-for-zero-divisors.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes(
        'divs-substitutes-zero-for-zero-divisors.stdout'
    )
    warning = expected_text(
        'divs-substitutes-zero-for-zero-divisors.stderr', source=source
    )
    # One warning per zero or empty divisor, as TAFC PB201214 prints them.
    assert run.stderr == warning.encode() * 4


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('ln_1.b', 'ln-diagnostics.stderr', id='ln-1'),
        pytest.param('ln_2.b', 'ln-diagnostics_2.stderr', id='ln-2'),
        pytest.param('ln_3.b', 'ln-diagnostics_2.stderr', id='ln-3'),
        pytest.param('ln_4.b', 'ln-diagnostics_3.stderr', id='ln-4'),
        pytest.param('ln_5.b', 'ln-diagnostics_3.stderr', id='ln-5'),
    ],
)
def test_ln_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/ln-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'ln-diagnostics_4.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('exp_1.b', 'exp-diagnostics.stderr', id='exp-1'),
        pytest.param('exp_2.b', 'exp-diagnostics_2.stderr', id='exp-2'),
        pytest.param('exp_3.b', 'exp-diagnostics_3.stderr', id='exp-3'),
    ],
)
def test_exp_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/exp-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'exp-diagnostics_4.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('sqrt_1.b', 'sqrt-diagnostics.stderr', id='sqrt-1'),
        pytest.param('sqrt_2.b', 'sqrt-diagnostics_2.stderr', id='sqrt-2'),
        pytest.param('sqrt_3.b', 'sqrt-diagnostics_3.stderr', id='sqrt-3'),
        pytest.param('sqrt_4.b', 'sqrt-diagnostics_3.stderr', id='sqrt-4'),
    ],
)
def test_sqrt_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/sqrt-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'sqrt-diagnostics_4.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, column, message_fixture, continues',
    [
        pytest.param(
            'power_1.b',
            5,
            'power-domain-and-diagnostics.stderr',
            True,
            id='power-1',
        ),
        pytest.param(
            'power_2.b',
            7,
            'power-domain-and-diagnostics_2.stderr',
            False,
            id='power-2',
        ),
        pytest.param(
            'power_3.b',
            7,
            'power-domain-and-diagnostics_3.stderr',
            False,
            id='power-3',
        ),
        pytest.param(
            'power_4.b',
            5,
            'power-domain-and-diagnostics_4.stderr',
            False,
            id='power-4',
        ),
    ],
)
def test_power_domain_and_diagnostics(
    compiler, fixture_name, column, message_fixture, continues
):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/power-domain-and-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert (run.returncode == 0) == continues
    assert run.stdout == (b'0\ndone\n' if continues else b'')
    assert (
        expected_text(
            'power-domain-and-diagnostics_5.stderr',
            source=source,
            column=column,
            message=message,
        ).encode()
        in run.stderr
    )


def test_randomize_wrong_argument_count(compiler):
    source = ROOT / 'tests/programs/randomize-wrong-argument-count.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('randomize-wrong-argument-count.stderr', source=source)
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param('rnd_1.b', 'rnd-invalid-bound.stderr', id='rnd-1'),
        pytest.param('rnd_2.b', 'rnd-invalid-bound.stderr', id='rnd-2'),
        pytest.param('rnd_3.b', 'rnd-invalid-bound_2.stderr', id='rnd-3'),
        pytest.param('rnd_4.b', 'rnd-invalid-bound_3.stderr', id='rnd-4'),
        pytest.param('rnd_5.b', 'rnd-invalid-bound_3.stderr', id='rnd-5'),
    ],
)
def test_rnd_invalid_bound(compiler, fixture_name, diagnostic_fixture):
    diagnostic = expected_text(diagnostic_fixture)
    source = ROOT / 'tests/programs/rnd-invalid-bound' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'rnd-invalid-bound_4.stderr', source=source, diagnostic=diagnostic
        ).encode()
        in run.stderr
    )


def test_bitxor_diagnostics(compiler):
    # Nonnumeric operands count as 0 (TAFC PB201214; see TAFC_OBSERVED).
    source = ROOT / 'tests/programs/bitxor-diagnostics/bitxor-variant-2.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('bitxor-diagnostics_2.stderr', source=source)
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, name',
    [
        pytest.param('mod_1.b', 'MOD', id='mod-1'),
        pytest.param('mod_2.b', 'MOD', id='mod-2'),
        pytest.param('mod_3.b', 'REM', id='mod-3'),
    ],
)
def test_mod_requires_numeric_operands(compiler, fixture_name, name):
    source = (
        ROOT / 'tests/programs/mod-requires-numeric-operands' / fixture_name
    )
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'mod-requires-numeric-operands.stderr', source=source, value_2=name
        ).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param('trim_1.b', 'trim-diagnostics.stderr', id='trim-1'),
        pytest.param('trim_2.b', 'trim-diagnostics_2.stderr', id='trim-2'),
    ],
)
def test_trim_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/trim-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'trim-diagnostics_3.stderr', source=source, message=message
        ).encode()
        in run.stderr
    )


def test_find_diagnostics(compiler):
    for fixture_name, error in (
        ('find_1.b', expected_text('find-diagnostics.stderr')),
        ('find_2.b', expected_text('find-diagnostics_2.stderr')),
        ('find_3.b', expected_text('find-diagnostics_3.stderr')),
    ):
        source = ROOT / 'tests/programs/find-diagnostics' / fixture_name
        run = subprocess.run(
            [CLI, source, '-o', compiler.c], capture_output=True, text=True
        )
        assert run.returncode != 0
        assert (
            expected_text(
                'find-diagnostics_4.stderr', source=source, error=error
            )
            in run.stderr
        )
    for case_number, keyword in enumerate(('FIND', 'FINDSTR'), 1):
        source = (
            ROOT
            / 'tests/programs/find-diagnostics'
            / f'find-variant-2_{case_number}.b'
        )
        run = compiler.run_native(source)
        assert run.returncode != 0
        assert (
            expected_text(
                'find-diagnostics_5.stderr', source=source, keyword=keyword
            ).encode()
            in run.stderr
        )


def test_swap_diagnostics(compiler):
    source = ROOT / 'tests/programs/swap-diagnostics/swap.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('swap-diagnostics.stderr', source=source).encode()
        in result.stderr
    )
    source = ROOT / 'tests/programs/swap-diagnostics/swap-variant-2.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('swap-diagnostics_2.stderr', source=source).encode()
        in result.stderr
    )


def test_ereplace_diagnostics(compiler):
    source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('ereplace-diagnostics.stderr', source=source).encode()
        in result.stderr
    )
    source = ROOT / 'tests/programs/ereplace-diagnostics/ereplace-variant-2.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert (
        expected_text('ereplace-diagnostics_2.stderr', source=source).encode()
        in result.stderr
    )


def test_change_diagnostics(compiler):
    for fixture_name, error in (
        ('change_1.b', expected_text('change-diagnostics.stderr')),
        ('change_2.b', expected_text('change-diagnostics_2.stderr')),
    ):
        source = ROOT / 'tests/programs/change-diagnostics' / fixture_name
        run = subprocess.run(
            [CLI, source, '-o', compiler.c], capture_output=True, text=True
        )
        assert run.returncode != 0
        assert (
            expected_text(
                'change-diagnostics_3.stderr', source=source, error=error
            )
            in run.stderr
        )
    source = ROOT / 'tests/programs/change-diagnostics/change-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('change-diagnostics_4.stderr', source=source).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'case_number, statement, expected_fixture',
    [
        pytest.param(
            1,
            "CONVERT 'a' TO 'x' IN Value",
            'string-mutations-check-conditionally-assigned-targets.stdout',
            id='convert-a-to-x-in-value',
        ),
        pytest.param(
            2,
            "CHANGE 'aa' TO 'x' IN Value<2>",
            'string-mutations-check-conditionally-assigned-targets_2.stdout',
            id='change-aa-to-x-in-value-2',
        ),
    ],
)
def test_string_mutations_check_conditionally_assigned_targets(
    compiler, case_number, statement, expected_fixture
):
    binary = compiler.work / 'mutate'
    expected = expected_bytes(expected_fixture)
    source = (
        ROOT
        / 'tests/programs/string-mutations-check-conditionally-assigned-targets'
        / f'mutate_{case_number}.b'
    )
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    found = subprocess.run([binary, 'found'], capture_output=True, timeout=5)
    assert (found.returncode, found.stdout, found.stderr) == (0, expected, b'')
    missing = subprocess.run(
        [binary, 'missing'], capture_output=True, timeout=5
    )
    column = statement.index('Value') + 1
    assert_unassigned_warning(
        missing,
        expected_text(
            'string-mutations-check-conditionally-assigned-targets.stderr',
            source=source,
            column=column,
        ),
    )


def test_neg_substitutes_zero(compiler):
    source = ROOT / 'tests/programs/neg-substitutes-zero.b'
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('neg-substitutes-zero.stdout')
    assert (
        run.stderr
        == expected_text('neg-substitutes-zero.stderr', source=source).encode()
    )


def test_negs_warns_for_nonnumeric_elements(compiler):
    source = ROOT / 'tests/programs/negs-warns-for-nonnumeric-elements.b'
    result = compiler.run_native(source)
    assert result.returncode == 0, result.stderr
    assert result.stdout == expected_bytes(
        'negs-warns-for-nonnumeric-elements.stdout'
    )
    warning = expected_text(
        'negs-warns-for-nonnumeric-elements.stderr', source=source
    )
    assert result.stderr == warning.encode() * 2


def test_abs_diagnostics(compiler):
    source = ROOT / 'tests/programs/abs-diagnostics/abs.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('abs-diagnostics.stderr', source=source).encode()
        in run.stderr
    )
    source = ROOT / 'tests/programs/abs-diagnostics/abs-variant-2.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert (
        expected_text('abs-diagnostics_2.stderr', source=source) in run.stderr
    )


def test_abss_diagnostics(compiler):
    source = ROOT / 'tests/programs/abss-diagnostics.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('abss-diagnostics.stderr', source=source).encode()
        in run.stderr
    )


def test_implicit_format_reports_uninitialized_mask_at_read(compiler):
    source = (
        ROOT
        / 'tests/programs/implicit-format-reports-uninitialized-mask-at-read.b'
    )
    run = compiler.run_native(source)
    assert_unassigned_warning(
        run,
        expected_text(
            'implicit-format-reports-uninitialized-mask-at-read.stderr',
            source=source,
        ),
    )


@pytest.mark.parametrize(
    'case_number, mask',
    [
        pytest.param(1, 'Q4', id='q4'),
        pytest.param(2, 'R2Q', id='r2q'),
        pytest.param(3, 'R%', id='r'),
        pytest.param(4, "3'xx'R", id='3-xx-r'),
        pytest.param(5, 'R2,%', id='r2-comma-percent'),
        pytest.param(6, '0T', id='0t'),
    ],
)
def test_fmt_diagnostics(compiler, case_number, mask):
    source = ROOT / 'tests/programs/fmt-diagnostics' / f'fmt_{case_number}.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text(
            'fmt-diagnostics.stderr', source=source, mask=mask
        ).encode()
        in run.stderr
    )


def test_index_diagnostics(compiler):
    source = ROOT / 'tests/programs/index-diagnostics/index.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert (
        expected_text('index-diagnostics.stderr', source=source)
        in result.stderr
    )
    source = ROOT / 'tests/programs/index-diagnostics/index-variant-2.b'
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('index-diagnostics_2.stderr', source=source).encode()
        in run.stderr
    )


def test_division_by_zero(compiler):
    source = ROOT / 'tests/programs/division-by-zero.b'
    run = compiler.run_native(source)
    # TAFC warns and continues (TAFC-CROSSCHECK.md section 3).
    assert run.returncode == 0
    assert (
        expected_text('division-by-zero.stderr', source=source).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param(
            'div_1.b',
            'div-requires-nonzero-numeric-operands.stderr',
            id='div-1',
        ),
        pytest.param(
            'div_2.b',
            'div-requires-nonzero-numeric-operands_2.stderr',
            id='div-2',
        ),
        pytest.param(
            'div_3.b',
            'div-requires-nonzero-numeric-operands_2.stderr',
            id='div-3',
        ),
    ],
)
def test_div_requires_nonzero_numeric_operands(
    compiler, fixture_name, diagnostic_fixture
):
    diagnostic = expected_text(diagnostic_fixture)
    source = (
        ROOT
        / 'tests/programs/div-requires-nonzero-numeric-operands'
        / fixture_name
    )
    run = compiler.run_native(source)
    # TAFC warns and continues (TAFC-CROSSCHECK.md section 3).
    assert run.returncode == 0
    assert (
        expected_text(
            'div-requires-nonzero-numeric-operands_3.stderr',
            source=source,
            diagnostic=diagnostic,
        ).encode()
        in run.stderr
    )


def test_compound_division_by_zero(compiler):
    source = ROOT / 'tests/programs/compound-division-by-zero.b'
    run = compiler.run_native(source)
    # TAFC warns and continues (TAFC-CROSSCHECK.md section 3).
    assert run.returncode == 0
    assert (
        expected_text(
            'compound-division-by-zero.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_insert_locations(compiler, subtests):
    fixtures = ROOT / 'tests/programs/insert-locations'
    source = fixtures / 'main.b'
    for variant, location in (
        ('1', expected_text('insert-locations.stderr')),
        ('2', expected_text('insert-locations_2.stderr')),
    ):
        with subtests.test(variant=variant):
            header = fixtures / variant / 'I_BROKEN'
            run = subprocess.run(
                [CLI, '-I', header.parent, source, '-o', compiler.c],
                text=True,
                capture_output=True,
            )
            assert run.returncode != 0
            assert str(header) + location in run.stderr
    header = fixtures / '3' / 'I_BROKEN'
    run = compiler.run_native(
        fixtures / 'main-variant-2.b', options=('-I', header.parent)
    )
    assert (
        expected_text('insert-locations_3.stderr', header=header).encode()
        in run.stderr
    )


def test_remove_shared_cursor(compiler):
    caller = ROOT / 'tests/programs/remove-shared-cursor/caller.b'
    sub = ROOT / 'tests/programs/remove-shared-cursor/take.b'
    run = compiler.run_native(caller, sub)
    assert run.returncode == 0, run.stderr
    assert run.stdout == expected_bytes('remove-shared-cursor.stdout')


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'bad_1.b', 'remove-expression-diagnostics.stderr', id='bad-1'
        ),
        pytest.param(
            'bad_2.b', 'remove-expression-diagnostics_2.stderr', id='bad-2'
        ),
    ],
)
def test_remove_expression_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = (
        ROOT / 'tests/programs/remove-expression-diagnostics' / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert str(source) + message in result.stderr


@pytest.mark.parametrize(
    'fixture_name, column',
    [
        pytest.param('statement-first.b', 19, id='statement-first'),
        pytest.param('expression-first.b', 16, id='expression-first'),
    ],
)
def test_remove_checks_conditionally_assigned_source(
    compiler, fixture_name, column
):
    binary = compiler.work / 'remove'
    fixtures = (
        ROOT / 'tests/programs/remove-checks-conditionally-assigned-source'
    )
    source = fixtures / fixture_name
    subprocess.run(
        [CLI, '--exe', source, '-o', binary],
        check=True,
        env=dict(os.environ, CC_FLAGS='-Wall -Wextra -Werror -pedantic'),
    )
    hit = subprocess.run([binary, 'hit'], capture_output=True, timeout=5)
    assert (hit.returncode, hit.stdout, hit.stderr) == (
        0,
        expected_bytes('remove-checks-conditionally-assigned-source.stdout'),
        b'',
    )
    miss = subprocess.run([binary, 'miss'], capture_output=True, timeout=5)
    assert_unassigned_warning(
        miss,
        expected_text(
            'remove-checks-conditionally-assigned-source.stderr',
            source=source,
            column=column,
        ),
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('matchfield_1.b', id='matchfield-1'),
        pytest.param('matchfield_2.b', id='matchfield-2'),
        pytest.param('matchfield_3.b', id='matchfield-3'),
    ],
)
def test_matchfield_invalid_field(compiler, fixture_name):
    source = ROOT / 'tests/programs/matchfield-invalid-field' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert (
        expected_text('matchfield-invalid-field.stderr', source=source).encode()
        in run.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, location, message',
    [
        ('asin-domain.b', '1:5', 'ASIN requires an operand from -1 to 1'),
        (
            'bitcheck-zero.b',
            '1:5',
            'bit number 0 applies only to BITSET and BITRESET',
        ),
        (
            'bitset-range.b',
            '2:5',
            'BITSET requires a bit number from -3 to 128',
        ),
        (
            'changetimestamp-fraction.b',
            '1:5',
            'CHANGETIMESTAMP requires whole adjustments',
        ),
        ('fadd-null.b', '1:5', 'FADD requires numeric operands'),
        ('fdiv-zero.b', '1:5', 'FDIV division by zero'),
    ],
    ids=lambda value: value if str(value).endswith('.b') else '',
)
def test_catalogue_function_diagnostics(
    compiler, fixture_name, location, message
):
    source = ROOT / 'tests/programs/catalogue-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert f'{source}:{location}: {message}\n'.encode() in run.stderr


# Element-wise operations, REUSE and integer overflow as TAFC PB201214 runs
# them under prime (observed reference run; TAFC-CROSSCHECK.md sections 2
# and 3). A missing or empty element is 0, a nonnumeric one warns and is
# 0, a zero divisor warns and gives 0, REUSE of a dynamic array has no
# effect, and integers do not overflow. Each program's .stdout holds TAFC's
# output without its warning lines, which jbcc writes to stderr.
TAFC_OBSERVED = [
    ('adds-diagnostics/adds_1.b', True),
    ('adds-diagnostics/adds_2.b', False),
    ('adds-diagnostics/adds_3.b', False),
    ('muls-diagnostics/muls_1.b', True),
    ('muls-diagnostics/muls_2.b', False),
    ('muls-diagnostics/muls_3.b', False),
    ('subs-diagnostics/subs_1.b', True),
    ('subs-diagnostics/subs_2.b', True),
    ('subs-diagnostics/subs_3.b', False),
    ('subs-diagnostics/subs_4.b', False),
    ('divs-diagnostics/divs_1.b', True),
    ('divs-diagnostics/divs_2.b', True),
    ('infix-reuse-division-reports-invalid-operands/reuse_1.b', True),
    ('infix-reuse-division-reports-invalid-operands/reuse_2.b', True),
    ('infix-reuse-division-reports-invalid-operands/reuse_3.b', True),
    ('integer-limits/numbers_1.b', False),
    ('integer-limits/numbers_2.b', True),
    ('fmts-invalid-mask/fmts_1.b', False),
    ('char-byte-range-diagnostics/char_3.b', False),
    ('iconv-diagnostics/date_1.b', False),
    ('iconv-diagnostics/date_2.b', False),
    ('iconv-diagnostics/date_3.b', False),
    ('iconv-diagnostics/date_4.b', False),
    ('iconv-diagnostics/date_5.b', False),
    ('iconv-diagnostics/date_6.b', False),
    ('iconv-diagnostics/date_7.b', False),
    ('iconv-diagnostics/date_8.b', False),
    ('iconv-diagnostics/date_9.b', False),
    ('iconv-diagnostics/date_10.b', False),
    # jbcc's own result: TAFC adds a byte after A.
    ('iconv-diagnostics/date_11.b', False),
    # A 00 pair is byte 0, as in TAFC.
    ('iconv-diagnostics/date_12.b', False),
    # jbcc's own result: TAFC gives 32767.
    ('iconv-diagnostics/date_13.b', False),
    ('oconv-diagnostics/date_1.b', False),
    ('oconv-diagnostics/date_2.b', False),
    ('oconv-diagnostics/date_3.b', False),
    ('oconv-diagnostics/date_4.b', False),
    ('oconv-diagnostics/date_5.b', False),
    ('oconv-diagnostics/date_6.b', False),
    ('catalogue-diagnostics/chars-range.b', False),
    ('sum-overflow.b', False),
    ('eqs-reuse-array.b', False),
    ('infix-reuse-requires-scalar.b', False),
    ('les-reuse-array.b', False),
    ('splice-reuse-array.b', False),
    ('bitxor-diagnostics/bitxor_1.b', False),
    ('bitxor-diagnostics/bitxor_2.b', False),
    ('delimited-bracket-assignment-diagnostics/fields_1.b', False),
    ('divs.b', True),
    ('infix-division-reuse.b', True),
]


@pytest.mark.parametrize(
    'name, warns', TAFC_OBSERVED, ids=[name for name, _ in TAFC_OBSERVED]
)
def test_element_operations_follow_tafc(compiler, name, warns):
    source = ROOT / 'tests/programs' / name
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == source.with_suffix('.stdout').read_bytes()
    if warns:
        assert b'warning' in run.stderr
    else:
        assert run.stderr == b''
