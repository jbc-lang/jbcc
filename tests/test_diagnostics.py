import subprocess

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


@pytest.mark.parametrize(
    'fixture_name, location_fixture',
    [
        pytest.param(
            'invalid_1.b',
            'diagnostics-preserve-existing-output.stderr',
            id='invalid-1-n-2',
        ),
        pytest.param(
            'invalid_2.b',
            'diagnostics-preserve-existing-output_2.stderr',
            id='invalid-2-begin-case',
        ),
        pytest.param(
            'invalid_3.b',
            'diagnostics-preserve-existing-output_3.stderr',
            id='invalid-3-begin-case',
        ),
        pytest.param(
            'invalid_4.b',
            'diagnostics-preserve-existing-output_2.stderr',
            id='invalid-4-begin-case-end-case',
        ),
        pytest.param(
            'invalid_5.b',
            'diagnostics-preserve-existing-output_4.stderr',
            id='invalid-5-crt-1-equ-x-to-2',
        ),
        pytest.param(
            'invalid_6.b',
            'diagnostics-preserve-existing-output_5.stderr',
            id='invalid-6-crt-1-equ-x-to-crt-2',
        ),
        pytest.param(
            'invalid_7.b',
            'diagnostics-preserve-existing-output_6.stderr',
            id='invalid-7-call-f-1',
        ),
        pytest.param(
            'invalid_8.b',
            'diagnostics-preserve-existing-output_7.stderr',
            id='invalid-8-call-f-1',
        ),
        pytest.param(
            'invalid_9.b',
            'diagnostics-preserve-existing-output_8.stderr',
            id='invalid-9-call-f-1',
        ),
        pytest.param(
            'invalid_10.b',
            'diagnostics-preserve-existing-output_9.stderr',
            id='invalid-10-open-f-x-else-stop',
        ),
        pytest.param(
            'invalid_11.b',
            'diagnostics-preserve-existing-output_10.stderr',
            id='invalid-11-open-x-else-stop',
        ),
        pytest.param(
            'invalid_12.b',
            'diagnostics-preserve-existing-output_11.stderr',
            id='invalid-12-rewind-on-2',
        ),
        pytest.param(
            'invalid_13.b',
            'diagnostics-preserve-existing-output_12.stderr',
            id='invalid-13-readt-x',
        ),
        pytest.param(
            'invalid_14.b',
            'diagnostics-preserve-existing-output_13.stderr',
            id='invalid-14-writet-x',
        ),
        pytest.param(
            'invalid_15.b',
            'diagnostics-preserve-existing-output_14.stderr',
            id='invalid-15-weof',
        ),
        pytest.param(
            'invalid_16.b',
            'diagnostics-preserve-existing-output_15.stderr',
            id='invalid-16-debug-1',
        ),
        pytest.param(
            'invalid_17.b',
            'diagnostics-preserve-existing-output_16.stderr',
            id='invalid-17-if-1-then-crt-1',
        ),
        pytest.param(
            'invalid_18.b',
            'diagnostics-preserve-existing-output_17.stderr',
            id='invalid-18-crt-done',
        ),
        pytest.param(
            'invalid_19.b',
            'diagnostics-preserve-existing-output_18.stderr',
            id='invalid-19-dim-a-2',
        ),
        pytest.param(
            'invalid_20.b',
            'diagnostics-preserve-existing-output_19.stderr',
            id='invalid-20-program',
        ),
        pytest.param(
            'invalid_21.b',
            'diagnostics-preserve-existing-output_20.stderr',
            id='invalid-21-function-f',
        ),
        pytest.param(
            'invalid_22.b',
            'diagnostics-preserve-existing-output_21.stderr',
            id='invalid-22-program-one-two',
        ),
        pytest.param(
            'invalid_23.b',
            'diagnostics-preserve-existing-output_22.stderr',
            id='invalid-23-n-1',
        ),
        pytest.param(
            'invalid_24.b',
            'diagnostics-preserve-existing-output_22.stderr',
            id='invalid-24-n-1',
        ),
        pytest.param(
            'invalid_25.b',
            'diagnostics-preserve-existing-output_23.stderr',
            id='invalid-25-go-1',
        ),
        pytest.param(
            'invalid_26.b',
            'diagnostics-preserve-existing-output_24.stderr',
            id='invalid-26-program-goto',
        ),
        pytest.param(
            'invalid_27.b',
            'diagnostics-preserve-existing-output_19.stderr',
            id='invalid-27-crt-1',
        ),
        pytest.param(
            'invalid_28.b',
            'diagnostics-preserve-existing-output_25.stderr',
            id='invalid-28-crt-unknown.function-3',
        ),
        pytest.param(
            'invalid_29.b',
            'diagnostics-preserve-existing-output_26.stderr',
            id='invalid-29-input-x',
        ),
        pytest.param(
            'invalid_30.b',
            'diagnostics-preserve-existing-output_27.stderr',
            id='invalid-30-id-1',
        ),
        pytest.param(
            'invalid_31.b',
            'diagnostics-preserve-existing-output_28.stderr',
            id='invalid-31-filename-1',
        ),
        pytest.param(
            'invalid_32.b',
            'diagnostics-preserve-existing-output_29.stderr',
            id='invalid-32-readnext-userno-else-stop',
        ),
        pytest.param(
            'invalid_33.b',
            'diagnostics-preserve-existing-output_30.stderr',
            id='invalid-33-read-userno-from-key-else-abort',
        ),
        pytest.param(
            'invalid_34.b',
            'diagnostics-preserve-existing-output_31.stderr',
            id='invalid-34-crt-rnd',
        ),
        pytest.param(
            'invalid_35.b',
            'diagnostics-preserve-existing-output_32.stderr',
            id='invalid-35-crt-dround-1-2-3',
        ),
        pytest.param(
            'invalid_36.b',
            'diagnostics-preserve-existing-output_33.stderr',
            id='invalid-36-crt-adds-x',
        ),
        pytest.param(
            'invalid_37.b',
            'diagnostics-preserve-existing-output_34.stderr',
            id='invalid-37-crt-subs-1',
        ),
        pytest.param(
            'invalid_38.b',
            'diagnostics-preserve-existing-output_35.stderr',
            id='invalid-38-crt-muls-1-2-3',
        ),
        pytest.param(
            'invalid_39.b',
            'diagnostics-preserve-existing-output_36.stderr',
            id='invalid-39-crt-reuse-2-3',
        ),
        pytest.param(
            'invalid_40.b',
            'diagnostics-preserve-existing-output_37.stderr',
            id='invalid-40-crt-2-reuse-3-4',
        ),
        pytest.param(
            'invalid_41.b',
            'diagnostics-preserve-existing-output_38.stderr',
            id='invalid-41-crt-sdiv-1',
        ),
        pytest.param(
            'invalid_42.b',
            'diagnostics-preserve-existing-output_38.stderr',
            id='invalid-42-crt-sdiv-1-2-3-4',
        ),
        pytest.param(
            'invalid_43.b',
            'diagnostics-preserve-existing-output_39.stderr',
            id='invalid-43-crt-divs-1',
        ),
        pytest.param(
            'invalid_44.b',
            'diagnostics-preserve-existing-output_40.stderr',
            id='invalid-44-crt-cats-x',
        ),
        pytest.param(
            'invalid_45.b',
            'diagnostics-preserve-existing-output_41.stderr',
            id='invalid-45-crt-compare-x',
        ),
        pytest.param(
            'invalid_46.b',
            'diagnostics-preserve-existing-output_42.stderr',
            id='invalid-46-crt-nes-1-2-3',
        ),
        pytest.param(
            'invalid_47.b',
            'diagnostics-preserve-existing-output_43.stderr',
            id='invalid-47-crt-eqs-x',
        ),
        pytest.param(
            'invalid_48.b',
            'diagnostics-preserve-existing-output_44.stderr',
            id='invalid-48-crt-num',
        ),
        pytest.param(
            'invalid_49.b',
            'diagnostics-preserve-existing-output_44.stderr',
            id='invalid-49-crt-num-1-2',
        ),
        pytest.param(
            'invalid_50.b',
            'diagnostics-preserve-existing-output_45.stderr',
            id='invalid-50-crt-iconv-20121231',
        ),
        pytest.param(
            'invalid_51.b',
            'diagnostics-preserve-existing-output_46.stderr',
            id='invalid-51-crt-fields-x',
        ),
        pytest.param(
            'invalid_52.b',
            'diagnostics-preserve-existing-output_47.stderr',
            id='invalid-52-crt-group-x',
        ),
        pytest.param(
            'invalid_53.b',
            'diagnostics-preserve-existing-output_47.stderr',
            id='invalid-53-crt-group-x-1-1-1',
        ),
        pytest.param(
            'invalid_54.b',
            'diagnostics-preserve-existing-output_48.stderr',
            id='invalid-54-crt-str-x',
        ),
        pytest.param(
            'invalid_55.b',
            'diagnostics-preserve-existing-output_49.stderr',
            id='invalid-55-crt-bytelen',
        ),
        pytest.param(
            'invalid_56.b',
            'diagnostics-preserve-existing-output_50.stderr',
            id='invalid-56-crt-utf8',
        ),
        pytest.param(
            'invalid_57.b',
            'diagnostics-preserve-existing-output_51.stderr',
            id='invalid-57-crt-latin1-a-b',
        ),
        pytest.param(
            'invalid_58.b',
            'diagnostics-preserve-existing-output_52.stderr',
            id='invalid-58-crt-lendp',
        ),
        pytest.param(
            'invalid_59.b',
            'diagnostics-preserve-existing-output_52.stderr',
            id='invalid-59-crt-lendp-a-b',
        ),
        pytest.param(
            'invalid_60.b',
            'diagnostics-preserve-existing-output_53.stderr',
            id='invalid-60-crt-itype',
        ),
        pytest.param(
            'invalid_61.b',
            'diagnostics-preserve-existing-output_53.stderr',
            id='invalid-61-crt-itype-a-b',
        ),
        pytest.param(
            'invalid_62.b',
            'diagnostics-preserve-existing-output_54.stderr',
            id='invalid-62-crt-replace-a-1-x',
        ),
        pytest.param(
            'invalid_63.b',
            'diagnostics-preserve-existing-output_55.stderr',
            id='invalid-63-crt-dquote',
        ),
        pytest.param(
            'invalid_64.b',
            'diagnostics-preserve-existing-output_56.stderr',
            id='invalid-64-crt-squote-1-2',
        ),
        pytest.param(
            'invalid_65.b',
            'diagnostics-preserve-existing-output_57.stderr',
            id='invalid-65-crt-ln',
        ),
        pytest.param(
            'invalid_66.b',
            'diagnostics-preserve-existing-output_58.stderr',
            id='invalid-66-crt-exp',
        ),
        pytest.param(
            'invalid_67.b',
            'diagnostics-preserve-existing-output_59.stderr',
            id='invalid-67-crt-sqrt-1-2',
        ),
        pytest.param(
            'invalid_68.b',
            'diagnostics-preserve-existing-output_60.stderr',
            id='invalid-68-crt-pwr-2',
        ),
        pytest.param(
            'invalid_69.b',
            'diagnostics-preserve-existing-output_61.stderr',
            id='invalid-69-crt-summation-1-2',
        ),
        pytest.param(
            'invalid_70.b',
            'diagnostics-preserve-existing-output_62.stderr',
            id='invalid-70-crt-trims-a-b',
        ),
        pytest.param(
            'invalid_71.b',
            'diagnostics-preserve-existing-output_63.stderr',
            id='invalid-71-crt-trimbs',
        ),
        pytest.param(
            'invalid_72.b',
            'diagnostics-preserve-existing-output_64.stderr',
            id='invalid-72-crt-trimfs-a-b',
        ),
        pytest.param(
            'invalid_73.b',
            'diagnostics-preserve-existing-output_65.stderr',
            id='invalid-73-crt-rem-1',
        ),
        pytest.param(
            'invalid_74.b',
            'diagnostics-preserve-existing-output_66.stderr',
            id='invalid-74-crt-mod-1',
        ),
        pytest.param(
            'invalid_75.b',
            'diagnostics-preserve-existing-output_67.stderr',
            id='invalid-75-crt-left-x',
        ),
        pytest.param(
            'invalid_76.b',
            'diagnostics-preserve-existing-output_68.stderr',
            id='invalid-76-crt-right-x-1-2',
        ),
        pytest.param(
            'invalid_77.b',
            'diagnostics-preserve-existing-output_69.stderr',
            id='invalid-77-crt-delete-a',
        ),
        pytest.param(
            'invalid_78.b',
            'diagnostics-preserve-existing-output_69.stderr',
            id='invalid-78-crt-delete-a-1-2-3-4',
        ),
        pytest.param(
            'invalid_79.b',
            'diagnostics-preserve-existing-output_70.stderr',
            id='invalid-79-crt-extract-a',
        ),
        pytest.param(
            'invalid_80.b',
            'diagnostics-preserve-existing-output_70.stderr',
            id='invalid-80-crt-extract-a-1-2-3-4',
        ),
        pytest.param(
            'invalid_81.b',
            'diagnostics-preserve-existing-output_71.stderr',
            id='invalid-81-crt-minimum',
        ),
        pytest.param(
            'invalid_82.b',
            'diagnostics-preserve-existing-output_72.stderr',
            id='invalid-82-crt-maximum-1-2',
        ),
        pytest.param(
            'invalid_83.b',
            'diagnostics-preserve-existing-output_73.stderr',
            id='invalid-83-crt-substrings-x-1',
        ),
        pytest.param(
            'invalid_84.b',
            'diagnostics-preserve-existing-output_74.stderr',
            id='invalid-84-crt-splice-a-b',
        ),
        pytest.param(
            'invalid_85.b',
            'diagnostics-preserve-existing-output_75.stderr',
            id='invalid-85-crt-trimf',
        ),
        pytest.param(
            'invalid_86.b',
            'diagnostics-preserve-existing-output_76.stderr',
            id='invalid-86-crt-trimb-a-b',
        ),
        pytest.param(
            'invalid_87.b',
            'diagnostics-preserve-existing-output_77.stderr',
            id='invalid-87-crt-alpha',
        ),
        pytest.param(
            'invalid_88.b',
            'diagnostics-preserve-existing-output_77.stderr',
            id='invalid-88-crt-alpha-a-b',
        ),
        pytest.param(
            'invalid_89.b',
            'diagnostics-preserve-existing-output_78.stderr',
            id='invalid-89-crt-isalpha',
        ),
        pytest.param(
            'invalid_90.b',
            'diagnostics-preserve-existing-output_79.stderr',
            id='invalid-90-crt-isdigit-1-2',
        ),
        pytest.param(
            'invalid_91.b',
            'diagnostics-preserve-existing-output_80.stderr',
            id='invalid-91-crt-neg',
        ),
        pytest.param(
            'invalid_92.b',
            'diagnostics-preserve-existing-output_80.stderr',
            id='invalid-92-crt-neg-1-2',
        ),
        pytest.param(
            'invalid_93.b',
            'diagnostics-preserve-existing-output_81.stderr',
            id='invalid-93-crt-upcase',
        ),
        pytest.param(
            'invalid_94.b',
            'diagnostics-preserve-existing-output_82.stderr',
            id='invalid-94-crt-lowcase-1-2',
        ),
        pytest.param(
            'invalid_95.b',
            'diagnostics-preserve-existing-output_83.stderr',
            id='invalid-95-crt-getenv-x-1',
        ),
        pytest.param(
            'invalid_96.b',
            'diagnostics-preserve-existing-output_84.stderr',
            id='invalid-96-crt-putenv-a-b',
        ),
        pytest.param(
            'invalid_97.b',
            'diagnostics-preserve-existing-output_85.stderr',
            id='invalid-97-r-1-2',
        ),
        pytest.param(
            'invalid_98.b',
            'diagnostics-preserve-existing-output_86.stderr',
            id='invalid-98-r-1-2-3-4-0',
        ),
        pytest.param(
            'invalid_99.b',
            'diagnostics-preserve-existing-output_87.stderr',
            id='invalid-99-close',
        ),
        pytest.param(
            'invalid_100.b',
            'diagnostics-preserve-existing-output_88.stderr',
            id='invalid-100-close-f-g-on-error-null',
        ),
        pytest.param(
            'invalid_101.b',
            'diagnostics-preserve-existing-output_25.stderr',
            id='invalid-101-crt-date-1',
        ),
        pytest.param(
            'invalid_102.b',
            'diagnostics-preserve-existing-output_25.stderr',
            id='invalid-102-crt-time-1',
        ),
        pytest.param(
            'invalid_103.b',
            'diagnostics-preserve-existing-output_25.stderr',
            id='invalid-103-crt-timedate-1',
        ),
        pytest.param(
            'invalid_104.b',
            'diagnostics-preserve-existing-output_89.stderr',
            id='invalid-104-for-i-1-to-2',
        ),
        pytest.param(
            'invalid_105.b',
            'diagnostics-preserve-existing-output_90.stderr',
            id='invalid-105-loop-while-0',
        ),
        pytest.param(
            'invalid_106.b',
            'diagnostics-preserve-existing-output_24.stderr',
            id='invalid-106-if-0-then-x-1',
        ),
    ],
)
def test_diagnostics_preserve_existing_output(
    compiler, fixture_name, location_fixture
):
    location = expected_text(location_fixture)
    source = (
        ROOT
        / 'tests/programs/diagnostics-preserve-existing-output'
        / fixture_name
    )
    compiler.c.write_text('previous output')
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert run.returncode != 0
    assert str(source) + location in run.stderr
    assert compiler.c.read_text() == 'previous output'


@pytest.mark.parametrize(
    'fixture_name, location_fixture',
    [
        pytest.param(
            'period_1.b', 'period-label-diagnostics.stderr', id='period-1'
        ),
        pytest.param(
            'period_2.b', 'period-label-diagnostics_2.stderr', id='period-2'
        ),
    ],
)
def test_period_label_diagnostics(compiler, fixture_name, location_fixture):
    location = expected_text(location_fixture)
    source = ROOT / 'tests/programs/period-label-diagnostics' / fixture_name
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert str(source) + location in result.stderr


@pytest.mark.parametrize(
    'fixture_name, column',
    [
        pytest.param('compare_1.b', 7, id='compare-1'),
        pytest.param('compare_2.b', 9, id='compare-2'),
        pytest.param('compare_3.b', 9, id='compare-3'),
    ],
)
def test_comparison_signs_keep_reference_spacing_rules(
    compiler, fixture_name, column
):
    source = (
        ROOT
        / 'tests/programs/comparison-signs-keep-reference-spacing-rules'
        / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'comparison-signs-keep-reference-spacing-rules.stderr',
        source=source,
        column=column,
    )


def test_cipher_diagnostics(compiler, subtests):
    fixtures = ROOT / 'tests/programs/cipher-diagnostics'
    for case_number, function in enumerate(('ENCRYPT', 'DECRYPT'), 1):
        with subtests.test(function=function):
            for method in (4, 5):
                with subtests.test(method=method):
                    source = fixtures / f'{function.lower()}-{method}.b'
                    result = compiler.run_native(source)
                    assert (result.returncode, result.stdout) == (
                        1,
                        expected_bytes('cipher-diagnostics.stdout'),
                    )
                    assert (
                        result.stderr
                        == expected_text(
                            'cipher-diagnostics.stderr',
                            source=source,
                            function=function,
                        ).encode()
                    )

            source = fixtures / f'crypt_{case_number}.b'
            result = subprocess.run(
                [CLI, source, '-o', compiler.c], text=True, capture_output=True
            )
            assert result.returncode == 1
            assert result.stderr == expected_text(
                'cipher-diagnostics_2.stderr', source=source, function=function
            )


def test_hexadecimal_conversion_diagnostics(compiler, subtests):
    for fixture_name in (
        'hex_1.b',
        'hex_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/programs/hexadecimal-conversion-diagnostics'
                / fixture_name
            )
            result = compiler.run_native(source)
            assert result.returncode != 0
            assert (
                expected_text(
                    'hexadecimal-conversion-diagnostics.stderr', source=source
                ).encode()
                in result.stderr
            )
    for fixture_name, function in (
        ('hex-variant-2_1.b', 'DTX'),
        ('hex-variant-2_2.b', 'XTD'),
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/programs/hexadecimal-conversion-diagnostics'
                / fixture_name
            )
            result = subprocess.run(
                [CLI, source, '-o', compiler.c], text=True, capture_output=True
            )
            assert result.returncode != 0
            assert (
                expected_text(
                    'hexadecimal-conversion-diagnostics_2.stderr',
                    source=source,
                    function=function,
                )
                in result.stderr
            )


def test_lit_equates_expand_quoted_source(compiler):
    main = ROOT / 'tests/programs/lit-equates-expand-quoted-source/main.b'
    show = ROOT / 'tests/programs/lit-equates-expand-quoted-source/show.b'
    run = compiler.run_native(main, show)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('lit-equates-expand-quoted-source.stdout'),
        b'',
    )


def test_lit_equate_diagnostic_points_inside_definition(compiler):
    definition = 'EQUATE BROKEN LIT "CRT MISSING"'
    include = (
        ROOT
        / 'tests/programs/lit-equate-diagnostic-points-inside-definition/I_INVALID'
    )
    source = (
        ROOT
        / 'tests/programs/lit-equate-diagnostic-points-inside-definition/main.b'
    )
    result = subprocess.run(
        [str(ROOT / 'jbcc'), str(source), '-o', str(compiler.work / 'main.c')],
        capture_output=True,
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'lit-equate-diagnostic-points-inside-definition.stderr',
            include=include,
            value_2=definition.index('MISSING') + 1,
        ).encode()
        in result.stderr
    )


def test_preprocessor_conditionals_and_include_guards(compiler):
    source = (
        ROOT
        / 'tests/programs/preprocessor-conditionals-and-include-guards/guarded.b'
    )
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('preprocessor-conditionals-and-include-guards.stdout'),
        b'',
    )


@pytest.mark.parametrize(
    'variant, location_fixture',
    [
        pytest.param(
            '1', 'preprocessor-conditional-diagnostics.stderr', id='1'
        ),
        pytest.param(
            '2', 'preprocessor-conditional-diagnostics_2.stderr', id='2'
        ),
        pytest.param(
            '3', 'preprocessor-conditional-diagnostics_3.stderr', id='3'
        ),
        pytest.param(
            '4', 'preprocessor-conditional-diagnostics_4.stderr', id='4'
        ),
        pytest.param(
            '5', 'preprocessor-conditional-diagnostics_5.stderr', id='5'
        ),
    ],
)
def test_preprocessor_conditional_diagnostics(
    compiler, variant, location_fixture
):
    fixtures = ROOT / 'tests/programs/preprocessor-conditional-diagnostics'
    source = fixtures / 'main.b'
    location = expected_text(location_fixture)
    include = fixtures / variant / 'I_BAD'
    result = subprocess.run(
        [CLI, '-I', include.parent, source, '-o', compiler.c],
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0
    assert str(include) + location in result.stderr


def test_duplicate_package_reports_its_source_location(compiler):
    source = ROOT / 'tests/programs/duplicate-package.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert (run.returncode, run.stderr) == (
        1,
        expected_text(
            'duplicate-package-reports-its-source-location.stderr',
            source=source,
        ),
    )


def test_source_encoding_preserves_legacy_and_utf8_literal_bytes(compiler):
    source = (
        ROOT
        / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/main.b'
    )
    routine = (
        ROOT
        / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/show.b'
    )
    result = compiler.run_native(
        source, routine, options=('--source-encoding', 'bytes')
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes(
            'source-encoding-preserves-legacy-and-utf8-literal-bytes.stdout'
        ),
        b'',
    )


def test_source_nul_is_ignored_in_comments(compiler):
    source = ROOT / 'tests/programs/source-nul-is-ignored-in-comments/main.b'
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('source-nul-is-ignored-in-comments.stdout'),
        b'',
    )


@pytest.mark.parametrize(
    'variant, column',
    [
        pytest.param('1', 10, id='1'),
        pytest.param('2', 12, id='2'),
        pytest.param('3', 11, id='3'),
        pytest.param('4', 17, id='4'),
    ],
)
def test_source_nul_reports_its_location_in_active_text(
    compiler, variant, column
):
    fixtures = (
        ROOT / 'tests/programs/source-nul-reports-its-location-in-active-text'
    )
    source = fixtures / 'main.b'
    include = fixtures / variant / 'I_VALUE'
    result = subprocess.run(
        [CLI, '-I', include.parent, source, '-o', compiler.c],
        text=True,
        capture_output=True,
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'source-nul-reports-its-location-in-active-text.stderr',
        include=include,
        column=column,
    )


def test_default_source_encoding_reports_invalid_utf8_in_an_include(compiler):
    source = (
        ROOT
        / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/main.b'
    )
    prefix = "* étoile "
    include = (
        ROOT
        / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/I_SHARED'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'default-source-encoding-reports-invalid-utf8-in-an-include.stderr',
        include=include,
        value_2=len(prefix) + 1,
    )
    assert not compiler.c.exists()


def test_ascii_and_ebcdic(compiler):
    (compiler.work / 'hello').write_bytes(
        bytes.fromhex('c8 85 93 93 96 40 91 c2 c3')
    )
    data = bytes(range(1, 256))
    (compiler.work / 'bytes').write_bytes(data)
    result = compiler.run_native(ROOT / 'tests/io/ebcdic.b', cwd=compiler.work)
    expected = (
        expected_bytes('ascii-and-ebcdic.stdout')
        + data.decode('cp037').encode('latin-1')
        + data.decode('latin-1').encode('cp037')
        + data
        + data
        + expected_bytes('ascii-and-ebcdic_2.stdout')
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected,
        b'',
    )


@pytest.mark.parametrize(
    'fixture_name, name',
    [
        pytest.param('invalid_1.b', 'ASCII', id='invalid-1'),
        pytest.param('invalid_2.b', 'EBCDIC', id='invalid-2'),
    ],
)
def test_ascii_and_ebcdic_argument_counts(compiler, fixture_name, name):
    source = (
        ROOT / 'tests/programs/ascii-and-ebcdic-argument-counts' / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'ascii-and-ebcdic-argument-counts.stderr',
            source=source,
            value_2=name,
        )
        in result.stderr
    )


def test_utf8_and_latin1_round_trip_all_nonzero_bytes(compiler):
    data = bytes(range(1, 256))
    (compiler.work / 'input').write_bytes(data)
    source = (
        ROOT / 'tests/programs/utf8-and-latin1-round-trip-all-nonzero-bytes.b'
    )
    result = compiler.run_native(source, cwd=compiler.work)
    expected = (
        data.decode('latin-1').encode('utf-8')
        + data
        + expected_bytes('utf8-and-latin1-round-trip-all-nonzero-bytes.stdout')
    )
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected,
        b'',
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('encoding_1.b', id='encoding-1'),
        pytest.param('encoding_2.b', id='encoding-2'),
        pytest.param('encoding_3.b', id='encoding-3'),
        pytest.param('encoding_4.b', id='encoding-4'),
        pytest.param('encoding_5.b', id='encoding-5'),
    ],
)
def test_latin1_rejects_malformed_and_unrepresentable_utf8(
    compiler, fixture_name
):
    source = (
        ROOT
        / 'tests/programs/latin1-rejects-malformed-and-unrepresentable-utf8'
        / fixture_name
    )
    result = compiler.run_native(source)
    assert result.returncode == 1
    assert result.stdout == b''
    assert (
        result.stderr
        == expected_text(
            'latin1-rejects-malformed-and-unrepresentable-utf8.stderr',
            source=source,
        ).encode()
    )


def test_seq_reads_block_bytes(compiler):
    (compiler.work / 'input').write_bytes(b'\x01\xfeAB')
    source = ROOT / 'tests/programs/seq-reads-block-bytes.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        0,
        expected_bytes('seq-reads-block-bytes.stdout'),
        b'',
    )


def test_seq_wrong_argument_count(compiler):
    source = ROOT / 'tests/programs/seq-wrong-argument-count.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode != 0
    assert (
        expected_text('seq-wrong-argument-count.stderr', source=source)
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name, message_fixture',
    [
        pytest.param(
            'char_1.b', 'char-byte-range-diagnostics.stderr', id='char-1'
        ),
        pytest.param(
            'char_2.b', 'char-byte-range-diagnostics_2.stderr', id='char-2'
        ),
        pytest.param(
            'char_3.b', 'char-byte-range-diagnostics_2.stderr', id='char-3'
        ),
    ],
)
def test_char_byte_range_diagnostics(compiler, fixture_name, message_fixture):
    message = expected_text(message_fixture)
    source = ROOT / 'tests/programs/char-byte-range-diagnostics' / fixture_name
    run = compiler.run_native(source)
    assert run.returncode != 0
    assert message.encode() in run.stderr
    assert (
        expected_text(
            'char-byte-range-diagnostics_3.stderr', source=source
        ).encode()
        in run.stderr
    )


def test_checksum_argument_diagnostics(compiler, subtests):
    for fixture_name in (
        'checksum_1.b',
        'checksum_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/programs/checksum-argument-diagnostics'
                / fixture_name
            )
            result = subprocess.run(
                [CLI, source, '-o', compiler.c], capture_output=True, text=True
            )
            assert result.returncode != 0
            assert (
                expected_text(
                    'checksum-argument-diagnostics.stderr', source=source
                )
                in result.stderr
            )

    source = (
        ROOT
        / 'tests/programs/checksum-argument-diagnostics/checksum-variant-2.b'
    )
    run = compiler.run_native(source)
    assert (run.returncode, run.stdout, run.stderr) == (
        1,
        b'',
        expected_text(
            'checksum-argument-diagnostics_2.stderr', source=source
        ).encode(),
    )
