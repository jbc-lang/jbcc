import subprocess

from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_diagnostics_preserve_existing_output(compiler, subtests):
    for fixture_name, location in (
        ('invalid_1.b', expected_text('diagnostics-preserve-existing-output.stderr')),
        ('invalid_2.b', expected_text('diagnostics-preserve-existing-output_2.stderr')),
        ('invalid_3.b', expected_text('diagnostics-preserve-existing-output_3.stderr')),
        ('invalid_4.b', expected_text('diagnostics-preserve-existing-output_2.stderr')),
        ('invalid_5.b', expected_text('diagnostics-preserve-existing-output_4.stderr')),
        ('invalid_6.b', expected_text('diagnostics-preserve-existing-output_5.stderr')),
        ('invalid_7.b', expected_text('diagnostics-preserve-existing-output_6.stderr')),
        ('invalid_8.b', expected_text('diagnostics-preserve-existing-output_7.stderr')),
        ('invalid_9.b', expected_text('diagnostics-preserve-existing-output_8.stderr')),
        ('invalid_10.b', expected_text('diagnostics-preserve-existing-output_9.stderr')),
        ('invalid_11.b', expected_text('diagnostics-preserve-existing-output_10.stderr')),
        ('invalid_12.b', expected_text('diagnostics-preserve-existing-output_11.stderr')),
        ('invalid_13.b', expected_text('diagnostics-preserve-existing-output_12.stderr')),
        ('invalid_14.b', expected_text('diagnostics-preserve-existing-output_13.stderr')),
        ('invalid_15.b', expected_text('diagnostics-preserve-existing-output_14.stderr')),
        ('invalid_16.b', expected_text('diagnostics-preserve-existing-output_15.stderr')),
        ('invalid_17.b', expected_text('diagnostics-preserve-existing-output_16.stderr')),
        ('invalid_18.b', expected_text('diagnostics-preserve-existing-output_17.stderr')),
        ('invalid_19.b', expected_text('diagnostics-preserve-existing-output_18.stderr')),
        ('invalid_20.b', expected_text('diagnostics-preserve-existing-output_19.stderr')),
        ('invalid_21.b', expected_text('diagnostics-preserve-existing-output_20.stderr')),
        ('invalid_22.b', expected_text('diagnostics-preserve-existing-output_21.stderr')),
        ('invalid_23.b', expected_text('diagnostics-preserve-existing-output_22.stderr')),
        ('invalid_24.b', expected_text('diagnostics-preserve-existing-output_22.stderr')),
        ('invalid_25.b', expected_text('diagnostics-preserve-existing-output_23.stderr')),
        ('invalid_26.b', expected_text('diagnostics-preserve-existing-output_24.stderr')),
        ('invalid_27.b', expected_text('diagnostics-preserve-existing-output_19.stderr')),
        ('invalid_28.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
        ('invalid_29.b', expected_text('diagnostics-preserve-existing-output_26.stderr')),
        ('invalid_30.b', expected_text('diagnostics-preserve-existing-output_27.stderr')),
        ('invalid_31.b', expected_text('diagnostics-preserve-existing-output_28.stderr')),
        ('invalid_32.b', expected_text('diagnostics-preserve-existing-output_29.stderr')),
        ('invalid_33.b', expected_text('diagnostics-preserve-existing-output_30.stderr')),
        ('invalid_34.b', expected_text('diagnostics-preserve-existing-output_31.stderr')),
        ('invalid_35.b', expected_text('diagnostics-preserve-existing-output_32.stderr')),
        ('invalid_36.b', expected_text('diagnostics-preserve-existing-output_33.stderr')),
        ('invalid_37.b', expected_text('diagnostics-preserve-existing-output_34.stderr')),
        ('invalid_38.b', expected_text('diagnostics-preserve-existing-output_35.stderr')),
        ('invalid_39.b', expected_text('diagnostics-preserve-existing-output_36.stderr')),
        ('invalid_40.b', expected_text('diagnostics-preserve-existing-output_37.stderr')),
        ('invalid_41.b', expected_text('diagnostics-preserve-existing-output_38.stderr')),
        ('invalid_42.b', expected_text('diagnostics-preserve-existing-output_38.stderr')),
        ('invalid_43.b', expected_text('diagnostics-preserve-existing-output_39.stderr')),
        ('invalid_44.b', expected_text('diagnostics-preserve-existing-output_40.stderr')),
        ('invalid_45.b', expected_text('diagnostics-preserve-existing-output_41.stderr')),
        ('invalid_46.b', expected_text('diagnostics-preserve-existing-output_42.stderr')),
        ('invalid_47.b', expected_text('diagnostics-preserve-existing-output_43.stderr')),
        ('invalid_48.b', expected_text('diagnostics-preserve-existing-output_44.stderr')),
        ('invalid_49.b', expected_text('diagnostics-preserve-existing-output_44.stderr')),
        ('invalid_50.b', expected_text('diagnostics-preserve-existing-output_45.stderr')),
        ('invalid_51.b', expected_text('diagnostics-preserve-existing-output_46.stderr')),
        ('invalid_52.b', expected_text('diagnostics-preserve-existing-output_47.stderr')),
        ('invalid_53.b', expected_text('diagnostics-preserve-existing-output_47.stderr')),
        ('invalid_54.b', expected_text('diagnostics-preserve-existing-output_48.stderr')),
        ('invalid_55.b', expected_text('diagnostics-preserve-existing-output_49.stderr')),
        ('invalid_56.b', expected_text('diagnostics-preserve-existing-output_50.stderr')),
        ('invalid_57.b', expected_text('diagnostics-preserve-existing-output_51.stderr')),
        ('invalid_58.b', expected_text('diagnostics-preserve-existing-output_52.stderr')),
        ('invalid_59.b', expected_text('diagnostics-preserve-existing-output_52.stderr')),
        ('invalid_60.b', expected_text('diagnostics-preserve-existing-output_53.stderr')),
        ('invalid_61.b', expected_text('diagnostics-preserve-existing-output_53.stderr')),
        ('invalid_62.b', expected_text('diagnostics-preserve-existing-output_54.stderr')),
        ('invalid_63.b', expected_text('diagnostics-preserve-existing-output_55.stderr')),
        ('invalid_64.b', expected_text('diagnostics-preserve-existing-output_56.stderr')),
        ('invalid_65.b', expected_text('diagnostics-preserve-existing-output_57.stderr')),
        ('invalid_66.b', expected_text('diagnostics-preserve-existing-output_58.stderr')),
        ('invalid_67.b', expected_text('diagnostics-preserve-existing-output_59.stderr')),
        ('invalid_68.b', expected_text('diagnostics-preserve-existing-output_60.stderr')),
        ('invalid_69.b', expected_text('diagnostics-preserve-existing-output_61.stderr')),
        ('invalid_70.b', expected_text('diagnostics-preserve-existing-output_62.stderr')),
        ('invalid_71.b', expected_text('diagnostics-preserve-existing-output_63.stderr')),
        ('invalid_72.b', expected_text('diagnostics-preserve-existing-output_64.stderr')),
        ('invalid_73.b', expected_text('diagnostics-preserve-existing-output_65.stderr')),
        ('invalid_74.b', expected_text('diagnostics-preserve-existing-output_66.stderr')),
        ('invalid_75.b', expected_text('diagnostics-preserve-existing-output_67.stderr')),
        ('invalid_76.b', expected_text('diagnostics-preserve-existing-output_68.stderr')),
        ('invalid_77.b', expected_text('diagnostics-preserve-existing-output_69.stderr')),
        ('invalid_78.b', expected_text('diagnostics-preserve-existing-output_69.stderr')),
        ('invalid_79.b', expected_text('diagnostics-preserve-existing-output_70.stderr')),
        ('invalid_80.b', expected_text('diagnostics-preserve-existing-output_70.stderr')),
        ('invalid_81.b', expected_text('diagnostics-preserve-existing-output_71.stderr')),
        ('invalid_82.b', expected_text('diagnostics-preserve-existing-output_72.stderr')),
        ('invalid_83.b', expected_text('diagnostics-preserve-existing-output_73.stderr')),
        ('invalid_84.b', expected_text('diagnostics-preserve-existing-output_74.stderr')),
        ('invalid_85.b', expected_text('diagnostics-preserve-existing-output_75.stderr')),
        ('invalid_86.b', expected_text('diagnostics-preserve-existing-output_76.stderr')),
        ('invalid_87.b', expected_text('diagnostics-preserve-existing-output_77.stderr')),
        ('invalid_88.b', expected_text('diagnostics-preserve-existing-output_77.stderr')),
        ('invalid_89.b', expected_text('diagnostics-preserve-existing-output_78.stderr')),
        ('invalid_90.b', expected_text('diagnostics-preserve-existing-output_79.stderr')),
        ('invalid_91.b', expected_text('diagnostics-preserve-existing-output_80.stderr')),
        ('invalid_92.b', expected_text('diagnostics-preserve-existing-output_80.stderr')),
        ('invalid_93.b', expected_text('diagnostics-preserve-existing-output_81.stderr')),
        ('invalid_94.b', expected_text('diagnostics-preserve-existing-output_82.stderr')),
        ('invalid_95.b', expected_text('diagnostics-preserve-existing-output_83.stderr')),
        ('invalid_96.b', expected_text('diagnostics-preserve-existing-output_84.stderr')),
        ('invalid_97.b', expected_text('diagnostics-preserve-existing-output_85.stderr')),
        ('invalid_98.b', expected_text('diagnostics-preserve-existing-output_86.stderr')),
        ('invalid_99.b', expected_text('diagnostics-preserve-existing-output_87.stderr')),
        ('invalid_100.b', expected_text('diagnostics-preserve-existing-output_88.stderr')),
        ('invalid_101.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
        ('invalid_102.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
        ('invalid_103.b', expected_text('diagnostics-preserve-existing-output_25.stderr')),
        ('invalid_104.b', expected_text('diagnostics-preserve-existing-output_89.stderr')),
        ('invalid_105.b', expected_text('diagnostics-preserve-existing-output_90.stderr')),
        ('invalid_106.b', expected_text('diagnostics-preserve-existing-output_24.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/diagnostics-preserve-existing-output' / fixture_name
            compiler.c.write_text('previous output')
            run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert run.returncode != 0
            assert str(source) + location in run.stderr
            assert compiler.c.read_text() == 'previous output'


def test_period_label_diagnostics(compiler, subtests):
    for fixture_name, location in (
        ('period_1.b', expected_text('period-label-diagnostics.stderr')),
        ('period_2.b', expected_text('period-label-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/period-label-diagnostics' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert str(source) + location in result.stderr


def test_comparison_signs_keep_reference_spacing_rules(compiler, subtests):
    for fixture_name, column in (
        ('compare_1.b', 7),
        ('compare_2.b', 9),
        ('compare_3.b', 9),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/comparison-signs-keep-reference-spacing-rules' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert result.returncode == 1
            assert (
                result.stderr
                == expected_text('comparison-signs-keep-reference-spacing-rules.stderr', source=source, column=column)
            )


def test_cipher_diagnostics(compiler, subtests):
    fixtures = ROOT / 'tests/programs/cipher-diagnostics'
    for case_number, function in enumerate(('ENCRYPT', 'DECRYPT'), 1):
        with subtests.test(function=function):
            for method in (4, 5):
                with subtests.test(method=method):
                    source = fixtures / f'{function.lower()}-{method}.b'
                    result = compiler.run_native(source)
                    assert (
                        (result.returncode, result.stdout)
                        == (1,
                             expected_bytes('cipher-diagnostics.stdout'))
                    )
                    assert (
                        result.stderr
                        == expected_text('cipher-diagnostics.stderr', source=source, function=function).encode()
                    )

            source = fixtures / f'crypt_{case_number}.b'
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode == 1
            assert (
                result.stderr
                == expected_text('cipher-diagnostics_2.stderr', source=source, function=function)
            )


def test_hexadecimal_conversion_diagnostics(compiler, subtests):
    for fixture_name in (
        'hex_1.b',
        'hex_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/hexadecimal-conversion-diagnostics' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode != 0
            assert (
                expected_text('hexadecimal-conversion-diagnostics.stderr', source=source).encode()
                in result.stderr
            )
    for fixture_name, function in (
        ('hex-variant-2_1.b', 'DTX'),
        ('hex-variant-2_2.b', 'XTD'),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/hexadecimal-conversion-diagnostics' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('hexadecimal-conversion-diagnostics_2.stderr', source=source, function=function)
                in result.stderr
            )


def test_lit_equates_expand_quoted_source(compiler):
    main = ROOT / 'tests/programs/lit-equates-expand-quoted-source/main.b'
    show = ROOT / 'tests/programs/lit-equates-expand-quoted-source/show.b'
    run = compiler.run_native(main, show)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (0,
             expected_bytes('lit-equates-expand-quoted-source.stdout'),
             b'')
    )


def test_lit_equate_diagnostic_points_inside_definition(compiler):
    definition = 'EQUATE BROKEN LIT "CRT MISSING"'
    include = ROOT / 'tests/programs/lit-equate-diagnostic-points-inside-definition/I_INVALID'
    source = ROOT / 'tests/programs/lit-equate-diagnostic-points-inside-definition/main.b'
    result = subprocess.run([str(ROOT / 'jbcc'), str(source), '-o', str(compiler.work / 'main.c')],
                            capture_output=True)
    assert result.returncode != 0
    assert (
        expected_text('lit-equate-diagnostic-points-inside-definition.stderr', include=include, value_2=definition.index('MISSING') + 1).encode()
        in result.stderr
    )


def test_preprocessor_conditionals_and_include_guards(compiler):
    source = ROOT / 'tests/programs/preprocessor-conditionals-and-include-guards/guarded.b'
    result = compiler.run_native(source)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('preprocessor-conditionals-and-include-guards.stdout'),
             b'')
    )


def test_preprocessor_conditional_diagnostics(compiler, subtests):
    fixtures = ROOT / 'tests/programs/preprocessor-conditional-diagnostics'
    source = fixtures / 'main.b'
    for variant, location in (
        ('1', expected_text('preprocessor-conditional-diagnostics.stderr')),
        ('2', expected_text('preprocessor-conditional-diagnostics_2.stderr')),
        ('3', expected_text('preprocessor-conditional-diagnostics_3.stderr')),
        ('4', expected_text('preprocessor-conditional-diagnostics_4.stderr')),
        ('5', expected_text('preprocessor-conditional-diagnostics_5.stderr')),
    ):
        with subtests.test(variant=variant):
            include = fixtures / variant / 'I_BAD'
            result = subprocess.run([CLI, '-I', include.parent, source, '-o', compiler.c],
                                    text=True, capture_output=True)
            assert result.returncode != 0
            assert str(include) + location in result.stderr


def test_duplicate_package_reports_its_source_location(compiler):
    source = ROOT / 'tests/programs/duplicate-package.b'
    run = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert (
        (run.returncode, run.stderr)
        == (1,
             expected_text('duplicate-package-reports-its-source-location.stderr', source=source))
    )


def test_source_encoding_preserves_legacy_and_utf8_literal_bytes(compiler):
    source = ROOT / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/main.b'
    routine = ROOT / 'tests/programs/source-encoding-preserves-legacy-and-utf8-literal-bytes/show.b'
    result = compiler.run_native(source, routine, options=('--source-encoding', 'bytes'))
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('source-encoding-preserves-legacy-and-utf8-literal-bytes.stdout'),
             b'')
    )


def test_source_nul_is_ignored_in_comments(compiler):
    source = ROOT / 'tests/programs/source-nul-is-ignored-in-comments/main.b'
    result = compiler.run_native(source)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('source-nul-is-ignored-in-comments.stdout'),
             b'')
    )


def test_source_nul_reports_its_location_in_active_text(compiler, subtests):
    fixtures = ROOT / 'tests/programs/source-nul-reports-its-location-in-active-text'
    source = fixtures / 'main.b'
    for variant, column in (('1', 10), ('2', 12), ('3', 11), ('4', 17)):
        with subtests.test(variant=variant):
            include = fixtures / variant / 'I_VALUE'
            result = subprocess.run([CLI, '-I', include.parent, source, '-o', compiler.c],
                                    text=True, capture_output=True)
            assert result.returncode == 1
            assert (
                result.stderr
                == expected_text('source-nul-reports-its-location-in-active-text.stderr', include=include, column=column)
            )


def test_default_source_encoding_reports_invalid_utf8_in_an_include(compiler):
    source = ROOT / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/main.b'
    prefix = "* étoile "
    include = ROOT / 'tests/programs/default-source-encoding-reports-invalid-utf8-in-an-include/I_SHARED'
    result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
    assert result.returncode == 1
    assert (
        result.stderr
        == expected_text('default-source-encoding-reports-invalid-utf8-in-an-include.stderr', include=include, value_2=len(prefix) + 1)
    )
    assert not compiler.c.exists()


def test_ascii_and_ebcdic(compiler):
    (compiler.work / 'hello').write_bytes(bytes.fromhex('c8 85 93 93 96 40 91 c2 c3'))
    data = bytes(range(1, 256))
    (compiler.work / 'bytes').write_bytes(data)
    result = compiler.run_native(ROOT / 'tests/io/ebcdic.b', cwd=compiler.work)
    expected = (expected_bytes('ascii-and-ebcdic.stdout') + data.decode('cp037').encode('latin-1')
                + data.decode('latin-1').encode('cp037') + data + data + expected_bytes('ascii-and-ebcdic_2.stdout'))
    assert (result.returncode, result.stdout, result.stderr) == (0, expected, b'')


def test_ascii_and_ebcdic_argument_counts(compiler, subtests):
    for fixture_name, name in (
        ('invalid_1.b', 'ASCII'),
        ('invalid_2.b', 'EBCDIC'),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/ascii-and-ebcdic-argument-counts' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
            assert result.returncode != 0
            assert (
                expected_text('ascii-and-ebcdic-argument-counts.stderr', source=source, value_2=name)
                in result.stderr
            )


def test_utf8_and_latin1_round_trip_all_nonzero_bytes(compiler):
    data = bytes(range(1, 256))
    (compiler.work / 'input').write_bytes(data)
    source = ROOT / 'tests/programs/utf8-and-latin1-round-trip-all-nonzero-bytes.b'
    result = compiler.run_native(source, cwd=compiler.work)
    expected = data.decode('latin-1').encode('utf-8') + data + expected_bytes('utf8-and-latin1-round-trip-all-nonzero-bytes.stdout')
    assert (result.returncode, result.stdout, result.stderr) == (0, expected, b'')


def test_latin1_rejects_malformed_and_unrepresentable_utf8(compiler, subtests):
    for fixture_name in (
        'encoding_1.b',
        'encoding_2.b',
        'encoding_3.b',
        'encoding_4.b',
        'encoding_5.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/latin1-rejects-malformed-and-unrepresentable-utf8' / fixture_name
            result = compiler.run_native(source)
            assert result.returncode == 1
            assert result.stdout == b''
            assert (
                result.stderr
                == expected_text('latin1-rejects-malformed-and-unrepresentable-utf8.stderr', source=source).encode()
            )


def test_seq_reads_block_bytes(compiler):
    (compiler.work / 'input').write_bytes(b'\x01\xfeAB')
    source = ROOT / 'tests/programs/seq-reads-block-bytes.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (
        (result.returncode, result.stdout, result.stderr)
        == (0,
             expected_bytes('seq-reads-block-bytes.stdout'),
             b'')
    )


def test_seq_wrong_argument_count(compiler):
    source = ROOT / 'tests/programs/seq-wrong-argument-count.b'
    result = subprocess.run([CLI, source, '-o', compiler.c], text=True, capture_output=True)
    assert result.returncode != 0
    assert expected_text('seq-wrong-argument-count.stderr', source=source) in result.stderr


def test_char_byte_range_diagnostics(compiler, subtests):
    for fixture_name, message in (
        ('char_1.b', expected_text('char-byte-range-diagnostics.stderr')),
        ('char_2.b', expected_text('char-byte-range-diagnostics_2.stderr')),
        ('char_3.b', expected_text('char-byte-range-diagnostics_2.stderr')),
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/char-byte-range-diagnostics' / fixture_name
            run = compiler.run_native(source)
            assert run.returncode != 0
            assert message.encode() in run.stderr
            assert expected_text('char-byte-range-diagnostics_3.stderr', source=source).encode() in run.stderr


def test_checksum_argument_diagnostics(compiler, subtests):
    for fixture_name in (
        'checksum_1.b',
        'checksum_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = ROOT / 'tests/programs/checksum-argument-diagnostics' / fixture_name
            result = subprocess.run([CLI, source, '-o', compiler.c], capture_output=True, text=True)
            assert result.returncode != 0
            assert expected_text('checksum-argument-diagnostics.stderr', source=source) in result.stderr

    source = ROOT / 'tests/programs/checksum-argument-diagnostics/checksum-variant-2.b'
    run = compiler.run_native(source)
    assert (
        (run.returncode, run.stdout, run.stderr)
        == (1,
             b'',
             expected_text('checksum-argument-diagnostics_2.stderr', source=source).encode())
    )
