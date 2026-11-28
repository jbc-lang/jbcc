import json
import os
import sqlite3
import subprocess
import sys

import pytest
from compiler_support import CLI, ROOT, expected_bytes, expected_text


def test_jbasecoredump_requires_an_application_snapshot_backend(
    compiler, subtests
):
    source = ROOT / 'tests/programs/jbasecoredump-missing-backend.b'
    result = compiler.run_native(source, cwd=compiler.work)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes(
            'jbasecoredump-requires-an-application-snapshot-backend.stdout'
        ),
        expected_text(
            'jbasecoredump-requires-an-application-snapshot-backend.stderr',
            source=source,
        ).encode(),
    )
    assert list(compiler.work.glob('JBASECOREDUMP*')) == []

    for fixture_name in (
        'snapshot_1.b',
        'snapshot_2.b',
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/programs/jbasecoredump-requires-an-application-snapshot-backend'
                / fixture_name
            )
            result = subprocess.run(
                [CLI, source, '-o', compiler.c], capture_output=True, text=True
            )
            assert result.returncode != 0
            assert (
                expected_text(
                    'jbasecoredump-requires-an-application-snapshot-backend_2.stderr',
                    source=source,
                )
                in result.stderr
            )


def test_validate_product_license_requires_a_backend_when_reached(compiler):
    source = (
        ROOT
        / 'tests/programs/validate-product-license-requires-a-backend-when-reached'
        / 'license.b'
    )
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes(
            'validate-product-license-requires-a-backend-when-reached.stdout'
        ),
        expected_text(
            'validate-product-license-requires-a-backend-when-reached.stderr',
            source=source,
        ).encode(),
    )


def test_itype_requires_backend_only_when_evaluation_is_reached(compiler):
    source = ROOT / 'tests/programs/itype-missing-backend.b'
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes(
            'itype-requires-backend-only-when-evaluation-is-reached.stdout'
        ),
        expected_text(
            'itype-requires-backend-only-when-evaluation-is-reached.stderr',
            source=source,
        ).encode(),
    )


@pytest.mark.parametrize(
    'fixture_name, call',
    [
        pytest.param('xml_1.b', "XMLTOXML('<doc/>', '', Code)", id='xml-1'),
        pytest.param(
            'xml_2.b', "XMLTODYN('<array/>', '', Codes(1))", id='xml-2'
        ),
        pytest.param('xml_3.b', "XMLTODYN('<array/>', '')", id='xml-3'),
        pytest.param('xml_4.b', "DYNTOXML('a':@FM:'b', '', Code)", id='xml-4'),
        pytest.param(
            'xml_5.b', "DYNTOXML('a':@FM:'b', '', Codes(1))", id='xml-5'
        ),
        pytest.param('xml_6.b', "DYNTOXML('a':@FM:'b', '')", id='xml-6'),
        pytest.param(
            'xml_7.b', "DYNTOXMLEXT('a':@FM:'b', '', Code)", id='xml-7'
        ),
    ],
)
def test_xml_transforms_require_a_backend_when_reached(
    compiler, fixture_name, call
):
    source = (
        ROOT
        / 'tests/programs/xml-transforms-require-a-backend-when-reached'
        / fixture_name
    )
    result = compiler.run_native(source)
    name = call.split('(', 1)[0]
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes('xml-transforms-require-a-backend-when-reached.stdout'),
        expected_text(
            'xml-transforms-require-a-backend-when-reached.stderr',
            source=source,
            value_2=name,
        ).encode(),
    )


@pytest.mark.parametrize(
    'name', ['DATELOCALETOGREGORIAN', 'DATEGREGORIANTOLOCALE']
)
def test_calendar_conversions_require_a_backend_when_reached(compiler, name):
    source = (
        ROOT
        / 'tests/programs/calendar-conversions-require-a-backend-when-reached'
        / f'{name.lower()}.b'
    )
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes(
            'calendar-conversions-require-a-backend-when-reached.stdout'
        ),
        expected_text(
            'calendar-conversions-require-a-backend-when-reached.stderr',
            source=source,
            value_2=name,
        ).encode(),
    )


@pytest.mark.parametrize(
    'fixture_name, name',
    [
        pytest.param('readxml.b', 'READXML', id='readxml'),
        pytest.param('readxmlu.b', 'READXMLU', id='readxmlu'),
    ],
)
def test_readxml_requires_a_backend_when_reached(compiler, fixture_name, name):
    source = (
        ROOT
        / 'tests/programs/readxml-requires-a-backend-when-reached'
        / fixture_name
    )
    result = compiler.run_native(source)
    assert (result.returncode, result.stdout, result.stderr) == (
        1,
        expected_bytes('readxml-requires-a-backend-when-reached.stdout'),
        expected_text(
            'readxml-requires-a-backend-when-reached.stderr',
            source=source,
            value_2=name,
        ).encode(),
    )


@pytest.mark.parametrize(
    'case_number, call, marker, message_fixture',
    [
        pytest.param(
            1,
            "XMLTODYN('<array/>')",
            ')',
            'xml-transform-argument-diagnostics.stderr',
            id='xmltodyn-array',
        ),
        pytest.param(
            2,
            "XMLTOXML('<doc/>', '', 0)",
            '0',
            'xml-transform-argument-diagnostics_2.stderr',
            id='xmltoxml-doc-0',
        ),
        pytest.param(
            3,
            "XMLTODYN('<array/>', '', Code<1>)",
            '<1>',
            'xml-transform-argument-diagnostics_3.stderr',
            id='xmltodyn-array-code-1',
        ),
        pytest.param(
            4,
            "XMLTOXML('<doc/>', '', Code, Extra)",
            ', Extra',
            'xml-transform-argument-diagnostics_3.stderr',
            id='xmltoxml-doc-code-extra',
        ),
        pytest.param(
            5,
            "DYNTOXML('a', '', 0)",
            '0',
            'xml-transform-argument-diagnostics_2.stderr',
            id='dyntoxml-a-0',
        ),
    ],
)
def test_xml_transform_argument_diagnostics(
    compiler, case_number, call, marker, message_fixture
):
    message = expected_text(message_fixture)
    statement = f'CRT {call}'
    source = (
        ROOT
        / 'tests/programs/xml-transform-argument-diagnostics'
        / f'xml_{case_number}.b'
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode != 0
    assert (
        expected_text(
            'xml-transform-argument-diagnostics_4.stderr',
            source=source,
            value_2=statement.rindex(marker) + 1,
            message=message,
        )
        in result.stderr
    )


@pytest.mark.parametrize(
    'fixture_name',
    [
        pytest.param('indices_1.b', id='indices-1'),
        pytest.param('indices_2.b', id='indices-2'),
    ],
)
def test_indices_requires_backend_only_when_a_query_is_reached(
    compiler, fixture_name
):
    source = (
        ROOT
        / 'tests/programs/indices-requires-backend-only-when-a-query-is-reached'
        / fixture_name
    )
    result = compiler.run_native(source, options=('--memory-file', 'BOOKS'))
    assert result.returncode == 1
    assert result.stdout == expected_bytes(
        'indices-requires-backend-only-when-a-query-is-reached.stdout'
    )
    assert (
        result.stderr
        == expected_text(
            'indices-requires-backend-only-when-a-query-is-reached.stderr',
            source=source,
        ).encode()
    )


def test_indices_requires_a_file_variable(compiler):
    source = ROOT / 'tests/programs/indices-requires-variable.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], text=True, capture_output=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'indices-requires-a-file-variable.stderr', source=source
    )


def test_debug_reports_location_only_when_reached(compiler):
    source = ROOT / 'tests/programs/debug-missing-backend.b'
    result = compiler.run_native(source)
    assert result.returncode != 0
    assert result.stdout == expected_bytes(
        'debug-reports-location-only-when-reached.stdout'
    )
    assert (
        result.stderr
        == expected_text(
            'debug-reports-location-only-when-reached.stderr', source=source
        ).encode()
    )


def test_callj_reports_missing_backend_only_when_reached(compiler):
    source = ROOT / 'tests/programs/callj-missing-backend.b'
    result = compiler.run_native(source)
    assert result.returncode == 1, result.stderr
    assert result.stdout == expected_bytes(
        'callj-reports-missing-backend-only-when-reached.stdout'
    )
    assert (
        result.stderr
        == expected_text(
            'callj-reports-missing-backend-only-when-reached.stderr',
            source=source,
        ).encode()
    )


def test_callj_requires_setting(compiler):
    source = ROOT / 'tests/programs/callj-missing-setting.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'callj-requires-setting.stderr', source=source
    )


@pytest.mark.parametrize(
    'case_number, keyword',
    [
        pytest.param(1, 'TRANSTART', id='transtart-1'),
        pytest.param(2, 'TRANSTART', id='transtart-2'),
        pytest.param(3, 'TRANSTART', id='transtart-3'),
        pytest.param(4, 'TRANSEND', id='transend'),
        pytest.param(5, 'TRANSABORT', id='transabort'),
    ],
)
def test_transactions_report_missing_backend_at_the_call(
    compiler, case_number, keyword
):
    source = (
        ROOT
        / 'tests/programs/transactions-report-missing-backend-at-the-call'
        / f'transactions_{case_number}.b'
    )
    result = compiler.run_native(source)
    assert result.returncode == 1, result.stderr
    assert result.stdout == expected_bytes(
        'transactions-report-missing-backend-at-the-call.stdout'
    )
    assert (
        result.stderr
        == expected_text(
            'transactions-report-missing-backend-at-the-call.stderr',
            source=source,
            keyword=keyword,
        ).encode()
    )


def test_transactions_require_a_conditional_arm(compiler):
    source = ROOT / 'tests/programs/transtart-missing-arm.b'
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'transactions-require-a-conditional-arm.stderr', source=source
    )


def test_transaction_dialect_reports_missing_backend(compiler, subtests):
    source = ROOT / 'tests/programs/transaction-dialect.b'
    binary = compiler.work / 'transactions'
    subprocess.run([CLI, '--exe', source, '-o', binary], check=True)
    run = subprocess.run([binary, 'skip'], capture_output=True, timeout=5)
    assert (run.returncode, run.stdout, run.stderr) == (
        0,
        expected_bytes('transaction-dialect-reports-missing-backend.stdout'),
        b'',
    )
    for operation, line in (('start', 4), ('commit', 6), ('abort', 8)):
        with subtests.test(operation=operation):
            run = subprocess.run(
                [binary, operation], capture_output=True, timeout=5
            )
            error = expected_text(
                'transaction-dialect-reports-missing-backend.stderr',
                source=source,
                line=line,
                value_3=operation.upper(),
            )
            assert (run.returncode, run.stdout, run.stderr) == (
                1,
                b'',
                error.encode(),
            )


def test_transaction_start_requires_a_conditional_arm(compiler):
    source = ROOT / 'tests/programs/transaction-start-missing-arm.b'
    run = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert (run.returncode, run.stderr) == (
        1,
        expected_text(
            'transaction-start-requires-a-conditional-arm.stderr', source=source
        ),
    )


def test_defc_declarations_and_runtime_diagnostics(compiler, subtests):
    for fixture_name, diagnostic in (
        ('foreign_1.b', b''),
        (
            'foreign_2.b',
            expected_bytes('defc-declarations-and-runtime-diagnostics.stderr'),
        ),
        (
            'foreign_3.b',
            expected_bytes(
                'defc-declarations-and-runtime-diagnostics_2.stderr'
            ),
        ),
        (
            'foreign_4.b',
            expected_bytes(
                'defc-declarations-and-runtime-diagnostics_3.stderr'
            ),
        ),
    ):
        with subtests.test(source=fixture_name):
            source = (
                ROOT
                / 'tests/programs/defc-declarations-and-runtime-diagnostics'
                / fixture_name
            )
            result = compiler.run_native(source)
            if diagnostic:
                assert (result.returncode, result.stdout) == (1, b'')
                assert result.stderr == os.fsencode(source) + diagnostic + b'\n'
            else:
                assert (result.returncode, result.stdout, result.stderr) == (
                    0,
                    expected_bytes(
                        'defc-declarations-and-runtime-diagnostics.stdout'
                    ),
                    b'',
                )


@pytest.mark.parametrize(
    'fixture_name, diagnostic_fixture',
    [
        pytest.param(
            'foreign_1.b',
            'defc-rejects-invalid-types-and-argument-counts.stderr',
            id='foreign-1',
        ),
        pytest.param(
            'foreign_2.b',
            'defc-rejects-invalid-types-and-argument-counts_2.stderr',
            id='foreign-2',
        ),
        pytest.param(
            'foreign_3.b',
            'defc-rejects-invalid-types-and-argument-counts_3.stderr',
            id='foreign-3',
        ),
    ],
)
def test_defc_rejects_invalid_types_and_argument_counts(
    compiler, fixture_name, diagnostic_fixture
):
    diagnostic = expected_text(diagnostic_fixture)
    source = (
        ROOT
        / 'tests/programs/defc-rejects-invalid-types-and-argument-counts'
        / fixture_name
    )
    result = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert result.returncode == 1
    assert result.stderr == f'{source}{diagnostic}\n'


def test_corpus_reports_deferred_reads_in_includes():
    corpus = ROOT / 'tests/corpus/deferred-include-reads'
    command = [sys.executable, ROOT / 'tools/check_corpus.py', corpus]
    strict = json.loads(subprocess.check_output(command, text=True))
    assert strict['files']['main.b'] == {
        'status': 'rejected',
        'diagnostic': "I_EXAMPLE:2:5: unknown variable or unsupported function 'Missing'",
    }
    deferred = json.loads(
        subprocess.check_output(
            command + ['--defer-unassigned-reads'], text=True
        )
    )
    assert deferred['first_blockers'] == {}
    assert deferred['files']['main.b'] == {
        'status': 'translated',
        'warnings': [
            "I_EXAMPLE:2:5: warning: read of 'Missing' before assignment is deferred to runtime"
        ],
    }


def test_corpus_t24_fixes_apply_in_memory_to_known_files(compiler, subtests):
    cases = {
        'STEST.AZ.PD.DATES.CHK': (
            b"EQUATE AZ.SLS.TYPE.I TO 2\r\nA = 'a':@FM:'b'\r\nB = A<.AZ.SLS.TYPE.I,1>\r\nCRT B\r\n",
            [(3, 7, '.AZ.SLS.TYPE.I', 'AZ.SLS.TYPE.I')],
        ),
        'TK.VALIDATE.SYSGEN.FILES': (
            b'* 1ST.RECORD = 1\n1ST.RECORD = 1\nIF 1ST.RECORD THEN CRT "1ST.RECORD"\n',
            [
                (2, 1, '1ST.RECORD', 'FIRST.RECORD'),
                (3, 4, '1ST.RECORD', 'FIRST.RECORD'),
            ],
        ),
        'LIST.DATA': (
            b'THE.ARGS = "F...":FM:"F..."\nCRT THE.ARGS\n',
            [(1, 19, 'FM', '@FM')],
        ),
    }
    for name, (source, _) in cases.items():
        (compiler.work / name).write_bytes(source)
    (compiler.work / 'nested').mkdir()
    (compiler.work / 'nested/LIST.DATA').write_bytes(cases['LIST.DATA'][0])

    command = [sys.executable, ROOT / 'tools/check_corpus.py', compiler.work]
    strict = json.loads(subprocess.check_output(command, text=True))
    reports = json.loads(
        subprocess.check_output(command + ['--t24-source-fixes'], text=True)
    )['files']
    for name, (source, edits) in cases.items():
        with subtests.test(name=name):
            assert strict['files'][name]['status'] == 'rejected'
            assert reports[name] == {
                'status': 'translated',
                'source_fixes': [
                    dict(
                        file=name,
                        line=line,
                        column=column,
                        before=before,
                        after=after,
                    )
                    for line, column, before, after in edits
                ],
            }
            assert (compiler.work / name).read_bytes() == source
    assert reports['nested/LIST.DATA'] == strict['files']['nested/LIST.DATA']


def test_r07_corpus_can_apply_source_fixes_and_report_include_stub():
    fixture = ROOT / 'tests/corpus/r07'
    root = fixture / '200707-R07'
    bp = root / 'GLOBUS.BP'
    original = {path: path.read_bytes() for path in bp.iterdir()}
    command = [sys.executable, ROOT / 'tools/check_corpus.py', root]
    baseline = json.loads(subprocess.check_output(command, text=True))['files']
    missing = 'GLOBUS.BP/LA.FIXTURE.b'
    compare = 'GLOBUS.BP/COMPARE.DB.JBASE'
    dates = 'GLOBUS.BP/STEST.AZ.PD.DATES.CHK'
    rates = 'GLOBUS.BP/MG.EOD.REDEFINE.CONTRACT.RATES'
    cdf = 'GLOBUS.BP/TU.LIB.STD.CDF'
    inv = 'GLOBUS.BP/TU.LIB.STD.INV'
    assert (
        "include file 'I_F.LA.PARAMETER' not found"
        in baseline[missing]['diagnostic']
    )
    assert baseline[dates]['status'] == 'rejected'
    assert baseline[rates] == {
        'status': 'rejected',
        'diagnostic': f"{rates}:5:14: expected 1 subscripts for 'CR.REC'",
    }
    assert baseline[cdf]['status'] == 'rejected'
    assert baseline[inv]['status'] == 'rejected'

    options = ['--t24-source-fixes', '--stub-r07-la-parameter']
    report = json.loads(subprocess.check_output(command + options, text=True))[
        'files'
    ]
    assert report[missing] == {
        'status': 'translated',
        'include_stubs': ['I_F.LA.PARAMETER'],
    }
    assert report[compare] == {
        'status': 'translated',
        'source_fixes': [
            dict(
                file=compare,
                line=1,
                column=10,
                before='/usr/jbc/include/JBC.h',
                after='JBC.h',
            )
        ],
    }
    assert report[dates] == {
        'status': 'translated',
        'source_fixes': [
            dict(
                file=dates,
                line=3,
                column=16,
                before='.AZ.SLS.TYPE.I',
                after='AZ.SLS.TYPE.I',
            )
        ],
    }
    assert report[rates] == {
        'status': 'translated',
        'source_fixes': [
            dict(file=rates, line=5, column=34, before=',1', after='')
        ],
    }
    assert report[cdf] == {
        'status': 'translated',
        'source_fixes': [
            dict(
                file=cdf,
                line=1,
                column=6,
                before='-3.125e-002',
                after='-0.03125',
            ),
            dict(file=cdf, line=2, column=6, before='1.25E2', after='125'),
        ],
    }
    assert report[inv] == {
        'status': 'translated',
        'source_fixes': [
            dict(
                file=inv, line=1, column=6, before='1.2300E+02', after='123.00'
            )
        ],
    }

    with_real_include = command + options + ['-I', fixture / 'real-includes']
    report = json.loads(subprocess.check_output(with_real_include, text=True))[
        'files'
    ]
    assert report[missing] == {'status': 'translated'}
    assert {path: path.read_bytes() for path in bp.iterdir()} == original


def test_r13_corpus_applies_source_fixes_in_t24_bp():
    # R13 T24.BP/STEST.AZ.PD.DATES.CHK line 63 keeps the leading-dot
    # selector seen in R10 and R07.
    root = ROOT / 'tests/corpus/r13/201307-R13'
    dates = 'T24.BP/STEST.AZ.PD.DATES.CHK'
    original = (root / dates).read_bytes()
    command = [sys.executable, ROOT / 'tools/check_corpus.py', root]
    baseline = json.loads(subprocess.check_output(command, text=True))['files']
    assert baseline[dates]['status'] == 'rejected'

    report = json.loads(
        subprocess.check_output(command + ['--t24-source-fixes'], text=True)
    )['files']
    assert report[dates] == {
        'status': 'translated',
        'source_fixes': [
            dict(
                file=dates,
                line=3,
                column=16,
                before='.AZ.SLS.TYPE.I',
                after='AZ.SLS.TYPE.I',
            )
        ],
    }
    assert (root / dates).read_bytes() == original


def test_r19_corpus_applies_source_fixes_by_path():
    # R19 AA I_DAS.AA.PRODUCT.LINE ends an EQU with a comma before the next
    # EQU line; the fix names the insert's path from the extract root.
    root = ROOT / 'tests/corpus/r19/201809-R19'
    source = 'AA/AA_ProductFramework/Source'
    unit = f'{source}/Private/DAS.AA.PRODUCT.LINE.b'
    insert = f'{source}/Public/I_DAS.AA.PRODUCT.LINE'
    original = (root / insert).read_bytes()
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        root,
        '-I',
        root / source / 'Public',
    ]
    baseline = json.loads(subprocess.check_output(command, text=True))['files']
    assert baseline[unit]['status'] == 'rejected'

    report = json.loads(
        subprocess.check_output(command + ['--t24-source-fixes'], text=True)
    )['files']
    assert report[unit] == {
        'status': 'translated',
        'source_fixes': [
            dict(file=insert, line=3, column=48, before=',', after='')
        ],
    }
    assert (root / insert).read_bytes() == original


def test_r19_corpus_can_exclude_the_test_framework():
    root = ROOT / 'tests/corpus/r19/201809-R19'
    unit = 'SE/SE_TestRetail/Source/Private/TestRetail.checkBalance.b'
    production = 'AA/AA_ProductFramework/Source/Private/DAS.AA.PRODUCT.LINE.b'
    command = [sys.executable, ROOT / 'tools/check_corpus.py', root]
    baseline = json.loads(subprocess.check_output(command, text=True))['files']
    assert baseline[unit]['status'] == 'rejected'

    report = json.loads(
        subprocess.check_output(
            command + ['--t24-exclude-test-framework'], text=True
        )
    )['files']
    assert report[unit] == {
        'status': 'excluded',
        'reason': 'T24 test framework component',
    }
    assert report[production]['status'] == baseline[production]['status']


def test_r13_corpus_can_exclude_local_routines():
    root = ROOT / 'tests/corpus/r13/201307-R13'
    local = 'T24.BP/V.PL.B2LIM.NET'
    command = [sys.executable, ROOT / 'tools/check_corpus.py', root]
    baseline = json.loads(subprocess.check_output(command, text=True))
    assert baseline['files'][local] == {
        'status': 'rejected',
        'diagnostic': f"{local}:2:1: include file 'I_F.PL.LOCAL.FIXTURE' not found",
    }

    option = ['--t24-exclude-local-routines']
    report = json.loads(subprocess.check_output(command + option, text=True))
    assert report['files'][local] == {
        'status': 'excluded',
        'reason': 'Raiffeisen Bank Polska local routine',
    }
    assert report['counts']['excluded'] == 1
    assert 'include file' not in report['first_blockers']


def test_corpus_report(compiler):
    (compiler.work / 'ok').write_text(
        'SUBROUTINE S(X)\nDEFFUN F()\nCALL OTHER(X)\n'
        'X = F(X)\nIF X THEN CALL S(X)\nCALL @X(X)\n'
    )
    (compiler.work / 'bad').write_text('MAT A = 2\n')
    (compiler.work / 'I_SHARED').write_text('EQU X TO 1\n')
    report = subprocess.run(
        [sys.executable, ROOT / 'tools/check_corpus.py', compiler.work],
        capture_output=True,
        text=True,
        check=True,
    )
    data = json.loads(report.stdout)
    assert data['counts'] == {
        'translated': 1,
        'rejected': 1,
        'include fragment': 1,
    }
    assert data['files']['ok']['status'] == 'translated'
    assert data['first_blockers'] == {"expected a dimensioned array 'A'": 1}
    assert 'bad:1:5:' in data['files']['bad']['diagnostic']


def test_corpus_can_summarize_next_name_mismatch_warnings():
    corpus = ROOT / 'tests/corpus/next-name-warnings'
    good = corpus / 'good.b'
    bad = corpus / 'bad.b'
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        corpus,
        '-j',
        '2',
    ]
    verbose = subprocess.run(
        command, capture_output=True, text=True, check=True
    )
    quiet = subprocess.run(
        command + ['--quiet-next-warnings'],
        capture_output=True,
        text=True,
        check=True,
    )
    report = json.loads(quiet.stdout)
    assert report == json.loads(verbose.stdout)
    assert report['files']['good.b']['status'] == 'translated'
    assert report['files']['bad.b']['status'] == 'rejected'
    for source in (good, bad):
        assert (
            expected_text(
                'corpus-can-summarize-next-name-mismatch-warnings.stderr',
                source=source,
            )
            in verbose.stderr
        )
    assert quiet.stderr.splitlines() == [
        expected_text(
            'corpus-can-summarize-next-name-mismatch-warnings_2.stderr',
            good=good,
        ),
        expected_text(
            'corpus-can-summarize-next-name-mismatch-warnings_3.stderr'
        ),
    ]


def test_corpus_api_coverage_counts_parsed_calls_by_form(compiler):
    fixture = ROOT / 'tests/corpus/api-coverage'
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        fixture / 'corpus',
        '--api-catalogue',
        fixture / 'spec',
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    entries = {
        (api['kind'], api['name']): api
        for api in report['api_coverage']['apis']
    }
    assert (
        entries['expression', 'ABS']['guide']
        == 'https://jbc-lang.org/pages/abs.html'
    )
    assert entries['expression', 'ABS']['nominal_arity'] == 1
    assert not any(
        (form['occurrences'] for form in entries['expression', 'ABS']['forms'])
    )
    assert entries['defc', 'Unused']['forms'] == []
    (bitor,) = entries['expression', 'BITOR']['forms']
    expected = {
        'arity': 2,
        'occurrences': 4,
        'units': 3,
        'c99_checked_units': 2,
    }
    assert {k: bitor[k] for k in expected} == expected
    assert bitor['example'] == {
        'unit': 'main.b',
        'file': 'I_EXAMPLE',
        'line': 1,
        'column': 16,
    }
    (native,) = entries['defc', 'CExample']['forms']
    assert (native['occurrences'], native['jbcc_support']) == (
        1,
        'backend required',
    )
    forms = {
        form['variant']: form['jbcc_support']
        for form in entries['expression', 'ENCRYPT']['forms']
    }
    assert forms == {
        'method 1 (ROT13)': 'ROT13 implemented',
        'method 4 (Base64)': 'backend required',
    }
    report_path = compiler.work / 'coverage.json'
    report_path.write_text(json.dumps(report))
    markdown = subprocess.check_output(
        [sys.executable, ROOT / 'tools/api_coverage.py', report_path], text=True
    )
    assert 'The `corpus` corpus scan passed strict C99 checking' in markdown
    assert (
        expected_text('corpus-api-coverage-counts-parsed-calls-by-form.stdout')
        in markdown
    )
    assert (
        expected_text(
            'corpus-api-coverage-counts-parsed-calls-by-form_2.stdout'
        )
        in markdown
    )


def test_corpus_uses_t24_catalog_kinds_for_selected_extract(compiler):
    fixture = ROOT / 'tests/corpus/file-catalog'
    catalog = compiler.work / 'catalog.sqlite'
    with sqlite3.connect(catalog) as db:
        db.executescript((fixture / 'catalog.sql').read_text())
    root = fixture / 'sample-r07'
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        root,
        '--t24-catalog',
        catalog,
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['counts'] == {
        'C header': 1,
        'include fragment': 1,
        'translated': 2,
    }
    assert (
        report['files']['GLOBUS.BP/Constants.h']['status'] == 'include fragment'
    )
    assert report['files']['GLOBUS.BP/Native.h']['status'] == 'C header'
    assert report['files']['GLOBUS.BP/I_Unit']['status'] == 'translated'
    assert report['files']['GLOBUS.BP/Main.b']['status'] == 'translated'


def test_corpus_index_resolves_and_reports_component_includes(compiler):
    fixture = ROOT / 'tests/corpus/indexed-includes'
    catalog = compiler.work / 'catalog.sqlite'
    with sqlite3.connect(catalog) as db:
        db.executescript((fixture / 'catalog.sql').read_text())
    root = fixture / 'sample-r19'
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        root,
        '--t24-catalog',
        catalog,
        '--t24-indexed-includes',
        '--source-prefix',
        'AA/Account',
        '-j',
        '2',
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['counts'] == {'translated': 2, 'rejected': 2}
    assert report['include_lookups'] == {
        'resolved': 4,
        'missing': 1,
        'ambiguous': 1,
    }
    twin = report['files']['AA/Account/Private/Twin.b']['include_lookups'][0]
    assert twin['status'] == 'resolved'
    assert twin['resolved'] == 'BB/Billing/Public/I_Twin'
    assert twin['identical_copies'] == [
        'BB/Billing/Public/I_Twin',
        'Flat/I_Twin',
    ]
    files = report['files']
    main = 'AA/Account/Private/Main.b'
    assert files[main]['package_directives'] == [
        dict(kind='package', name='AA.Account', file=main, line=1, column=10),
        dict(kind='using', name='BB.Billing', file=main, line=2, column=8),
    ]
    traces = files[main]['include_lookups']
    assert [(e['file'], e['rule'], e['resolved']) for e in traces] == [
        (main, 'source directory', 'AA/Account/Private/I_Local'),
        (main, 'component', 'AA/Account/Public/I_Choice'),
        (
            'AA/Account/Public/I_Choice',
            'release index',
            'BB/Billing/Public/I_Global',
        ),
    ]
    ambiguous = files['AA/Account/Private/Ambiguous.b']['include_lookups'][0]
    assert ambiguous['status'] == 'ambiguous'
    assert ambiguous['candidates'] == [
        'BB/Billing/Public/I_Tied',
        'Flat/I_Tied',
    ]
    missing = files['AA/Account/Private/Missing.b']
    assert missing['include_lookups'][0]['status'] == 'missing'
    assert missing['package_directives'][0]['name'] == 'AA.Account'


def test_corpus_generates_domain_inserts_from_catalogued_classes(compiler):
    fixture = ROOT / 'tests/corpus/domain-inserts'
    catalog = compiler.work / 'catalog.sqlite'
    with sqlite3.connect(catalog) as db:
        db.executescript((fixture / 'catalog.sql').read_text())
    generated = compiler.work / 'domain-inserts'
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        fixture / 'sample-r19',
        '--t24-catalog',
        catalog,
        '--t24-indexed-includes',
        '--t24-domain-inserts',
        generated,
        '--source-prefix',
        'Shop',
        '-j',
        '2',
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['counts'] == {'translated': 1, 'rejected': 2}
    assert report['include_lookups'] == {
        'generated': 1,
        'resolved': 1,
        'missing': 1,
        'ambiguous': 1,
    }
    files = report['files']
    uses = 'Shop/Shop_Orders/Source/Private/Uses.b'
    domain = 'Shop/Shop_Orders/Definition/OrderDomain.domain'
    assert [
        (e['target'], e['status'], e.get('domain'))
        for e in files[uses]['include_lookups']
    ] == [
        ('I_OrderService_Line', 'generated', domain),
        ('I_OrderService_Header', 'resolved', None),
    ]
    assert (generated / 'I_OrderService_Line').read_text().splitlines()[
        -4:
    ] == [
        'EQU Line.sku TO 1',
        'EQU Line.quantity TO 2',
        'EQU Line.notes TO 3',
        'EQU Line.header TO 4',
    ]
    assert not (generated / 'I_OrderService_Header').exists()
    missing = files['Shop/Shop_Orders/Source/Private/Missing.b']
    assert missing['status'] == 'rejected'
    assert missing['include_lookups'][0]['status'] == 'missing'
    assert missing['include_lookups'][0]['domain_class'] == 'absent'
    ambiguous = files['Shop/Shop_Orders/Source/Private/Ambiguous.b']
    assert ambiguous['include_lookups'][0]['candidates'] == [
        'Shop/Shop_Archive/Definition/ArchiveDomain.domain',
        domain,
    ]
    assert 'ambiguous domain class' in ambiguous['diagnostic']

    without = command[:6] + command[8:]
    report = json.loads(subprocess.check_output(without, text=True))
    assert report['files'][uses]['include_lookups'][0]['status'] == 'missing'

    excluded = json.loads(
        subprocess.check_output(
            command + ['--t24-exclude-missing-domains'], text=True
        )
    )['files']
    assert excluded['Shop/Shop_Orders/Source/Private/Missing.b']['status'] == 'excluded'
    assert excluded['Shop/Shop_Orders/Source/Private/Missing.b']['reason'] == (
        'generated insert I_OrderService_Unknown has no .domain class in the dump'
    )
    assert excluded[uses]['status'] == files[uses]['status']
    assert excluded['Shop/Shop_Orders/Source/Private/Ambiguous.b']['status'] == 'rejected'


def test_corpus_checks_qualified_component_signatures(compiler):
    fixture = ROOT / 'tests/corpus/component-calls'
    catalog = compiler.work / 'catalog.sqlite'
    with sqlite3.connect(catalog) as db:
        db.executescript((fixture / 'catalog.sql').read_text())
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        fixture / 'sample-r19',
        '--t24-catalog',
        catalog,
        '--t24-component-calls',
        '-j',
        '2',
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['counts'] == {'translated': 1, 'rejected': 14}
    assert report['selection']['component_calls']
    assert report['files']['Main.b']['status'] == 'translated'
    assert report['files']['Main.b']['warnings'] == [
        "Main.b:57:10: warning: table 'Shop.Prices.Archive' is not declared "
        "by its component; using the standard table operations",
        "Main.b:68:1: warning: component member 'Shop.Prices.setDrawings' "
        "is not declared by its component; accepting its arguments",
        "Main.b:69:5: warning: component member 'Shop.Prices.getDrawings' "
        "is not declared by its component; accepting its arguments",
    ]
    failures = {
        'WrongArity.b': "2:5: arguments disagree with component declaration for 'Shop.Prices.getCurrent'",
        'WrongKind.b': "3:5: arguments disagree with component declaration for 'Shop.Prices.Format'",
        'PrivateAccess.b': "2:1: component member 'Shop.Prices.Reset' has private access",
        'ModuleAccess.b': "2:1: component member 'Shop.Prices.Clear' has module access",
        'MissingSharedMember.b': "3:1: unsupported statement 'Shop.Shared.setClash'",
        'PrivateTableAccess.b': "2:5: component member 'Shop.Prices.Ledger.Read' has private access",
        'WrongTableArity.b': "2:1: arguments disagree with component declaration for 'Shop.Prices.Prices.Write'",
        'VoidExpression.b': "2:5: component method 'Shop.Prices.setCurrent' has no return value",
        'InterfaceWithoutMethodName.b': "2:1: arguments disagree with component declaration for 'Shop.Prices.priceCheck'",
        'WrongRank.b': "2:5: arguments disagree with component declaration for 'Shop.Prices.getGrid'",
        'UnknownComponentTable.b': "2:10: unknown variable or unsupported function 'Shop.Missing.Archive.Read'",
        'UndeclaredTableOperation.b': "2:1: unsupported statement 'Shop.Prices.Archive.Rebuild'",
        'StubbedMember.b': "3:10: arguments disagree with component declaration for 'TF.L3Helper.testPublishedMethod'",
        'UnknownComponentAccessor.b': "2:5: unknown variable or unsupported function 'Shop.Missing.getDrawings'",
    }
    for name, diagnostic in failures.items():
        assert report['files'][name]['diagnostic'] == f'{name}:{diagnostic}'


def test_corpus_can_stub_void_results_for_testing(compiler):
    fixture = ROOT / 'tests/corpus/component-calls'
    catalog = compiler.work / 'catalog.sqlite'
    with sqlite3.connect(catalog) as db:
        db.executescript((fixture / 'catalog.sql').read_text())
    command = [
        sys.executable,
        ROOT / 'tools/check_corpus.py',
        fixture / 'sample-r19',
        '--t24-catalog',
        catalog,
        '--t24-component-calls',
        '--t24-stub-void-results',
    ]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['files']['VoidExpression.b'] == {
        'status': 'translated',
        'package_directives': report['files']['VoidExpression.b'][
            'package_directives'
        ],
        'warnings': [
            "VoidExpression.b:2:5: warning: component method "
            "'Shop.Prices.setCurrent' has no return value; using 0 for testing"
        ],
    }
    assert report['files']['WrongArity.b']['status'] == 'rejected'

    relaxed = json.loads(
        subprocess.check_output(command + ['--t24-relax-access'], text=True)
    )['files']['PrivateAccess.b']
    assert relaxed['status'] == 'translated'
    assert relaxed['warnings'] == [
        "PrivateAccess.b:2:1: warning: component member 'Shop.Prices.Reset' "
        "has private access; allowed for testing"
    ]

    stubbed = json.loads(
        subprocess.check_output(command + ['--t24-stub-members'], text=True)
    )['files']['StubbedMember.b']
    assert stubbed['status'] == 'translated'
    assert stubbed['warnings'] == [
        "StubbedMember.b:3:10: warning: component member "
        "'TF.L3Helper.testPublishedMethod' is stubbed for testing"
    ]


def test_corpus_report_can_preserve_source_bytes():
    corpus = ROOT / 'tests/corpus/legacy-include-bytes'
    command = [sys.executable, ROOT / 'tools/check_corpus.py', corpus]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['counts'] == {'encoding': 1, 'include fragment': 1}
    assert report['files']['main.b'] == {
        'status': 'encoding',
        'diagnostic': 'I_SHARED:1:10: invalid UTF-8 at byte 0xfd',
    }
    report = json.loads(
        subprocess.check_output(
            command + ['--source-encoding', 'bytes'], text=True
        )
    )
    assert report['counts'] == {'translated': 1, 'include fragment': 1}


def test_corpus_matrix_signatures(compiler):
    (compiler.work / 'forward').write_text(
        'SUBROUTINE F(MAT A)\nCALL EXT(MAT A)\nIF 0 THEN CALL F(MAT A)\n'
    )
    (compiler.work / 'mixed').write_text(
        'DIM A(1)\nCALL EXT(MAT A)\nCALL EXT(A(1))\n'
    )
    result = subprocess.run(
        [sys.executable, ROOT / 'tools/check_corpus.py', compiler.work],
        capture_output=True,
        text=True,
        check=True,
    )
    files = json.loads(result.stdout)['files']
    assert files['forward']['status'] == 'translated'
    assert (
        'mixed:3:6: external calls disagree on signature'
        in files['mixed']['diagnostic']
    )


def test_corpus_checks_external_arities_and_reports_the_linkage_conflict(
    compiler,
):
    source = compiler.work / 'caller'
    source.write_text("CALL Report('')\nCALL Report\n")
    command = [sys.executable, ROOT / 'tools/check_corpus.py', compiler.work]
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['first_blockers'] == {}
    assert report['files']['caller'] == {
        'status': 'translated',
        'linkage_diagnostic': "caller:2:6: calls to 'Report' use different argument counts (1 and 0)",
    }

    definition = compiler.work / 'report'
    definition.write_text('SUBROUTINE Report(Value)\nCRT Value\n')
    result = subprocess.run(
        [CLI, source, definition, '-o', compiler.c],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 1
    assert result.stderr == expected_text(
        'corpus-checks-external-arities-and-reports-the-linkage-conflict.stderr',
        source=source,
    )

    source.write_text('SUBROUTINE Recur(MAT A)\nCALL Recur\n')
    report = json.loads(subprocess.check_output(command, text=True))
    assert report['files']['caller'] == {
        'status': 'rejected',
        'diagnostic': 'caller:2:6: recursive call has incompatible signature',
    }


def test_testcase_units_translate(compiler):
    """A T24 unit test (*.tut, TUT.md) translates: TESTCASE names the
    program, UTF calls take scalars by reference, expressions by value and
    whole matrices. Built alone, the test fails at runTest: its target
    isn't linked."""
    source = ROOT / 'tests/programs/testcase/sample.tut'
    generated = subprocess.run(
        [CLI, source, '-o', compiler.c], capture_output=True, text=True
    )
    assert generated.returncode == 0, generated.stderr
    c = compiler.c.read_text()
    assert '#define JBC_UTF 1' in c
    assert 'jbc_utf("addParam", 1, (jbc_utf_argument[]){{&' in c
    assert c.count('jbc_utf("addParam", 1, (jbc_utf_argument[]){{NULL, (jbc_matrix)') == 2
    run = compiler.run_native(source)
    assert run.returncode == 3
    assert b"target 'SAMPLE.ROUTINE' is not a routine of the program" in run.stderr


TESTCASES = ROOT / 'tests/programs/testcase'


def test_utf_runs_a_subroutine_target(compiler):
    """UTF.runTest calls the target with the parameters by reference; the
    test asserts on them afterwards. reset clears the parameters, and the
    first failing check is the verdict (exit status 3)."""
    run = compiler.run_native(TESTCASES / 'split.tut', TESTCASES / 'SAMPLE.SPLIT.b')
    assert run.returncode == 3
    assert run.stderr.endswith(
        b'split.tut:23:5: UTF.assertEquals("1", "2"): deliberately wrong\n'
    ), run.stderr
    assert run.stderr.startswith(b'UTF: failed 1, first at ')


def test_utf_runs_a_function_target(compiler):
    """runTest returns a FUNCTION target's result; setParam replaces a
    parameter; the other checks hold."""
    run = compiler.run_native(TESTCASES / 'twice.tut', TESTCASES / 'SAMPLE.TWICE.b')
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 6 checks in 2 runs\n')


def utf_build(compiler, *sources, **options):
    """Build a unit test with compile_program's options, as
    tools/run_tuts.py links one, and run it."""
    translate = (
        "import sys, json; from pathlib import Path; from jbcc.compiler import compile_program; "
        "source, _ = compile_program([Path(p) for p in sys.argv[3:]], [], **json.loads(sys.argv[2])); "
        "Path(sys.argv[1]).write_text(source)"
    )
    subprocess.run(
        [sys.executable, '-c', translate, compiler.c, json.dumps(options),
         *(TESTCASES / source for source in sources)],
        check=True,
        env={**os.environ, 'PYTHONPATH': str(ROOT / 'src')},
    )
    program = compiler.work / 'utf-test'
    subprocess.run(
        ['cc', '-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic', compiler.c, '-o', program],
        check=True,
    )
    return subprocess.run([program], capture_output=True)


def test_utf_target_aliases_and_missing_parameters(compiler):
    """An alias names a routine, as an R19 component method does; missing
    trailing parameters are empty, and setParam pads before its position."""
    run = utf_build(
        compiler, 'padded.tut', 'SAMPLE.SPLIT.b', utf_aliases={'Sample.Split': 'SAMPLE.SPLIT'}
    )
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 2 checks in 1 runs\n')


def test_utf_stubs_answer_the_targets_calls(compiler):
    """With stub_missing, each routine the program doesn't define answers
    from the test's stubs: expected arguments (a value, any() or a
    matcher), returned values or same(), a FUNCTION's result, a COMMON
    change, setRepeatable and invocation counts. Stub names match calls
    whatever their case; reset clears the stubs. Of the matching stubs the
    most specific answers, and of equally specific ones the newest."""
    run = utf_build(compiler, 'stubbed.tut', 'SAMPLE.LOOKUP.b', stub_missing=True)
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 7 checks in 2 runs\n')


def test_utf_call_that_no_stub_matches_fails(compiler):
    run = utf_build(compiler, 'unmatched.tut', 'SAMPLE.LOOKUP.b', stub_missing=True)
    assert run.returncode == 3
    assert run.stderr.endswith(
        b'UTF: failed 2, first at the target called SAMPLE.FETCH("KX", ""), '
        b'which no stub matches\n'
    ), run.stderr


def test_utf_stubs_chained_by_property_conditions(compiler):
    """addStubPropertyCondition makes a stub answer only while a property
    has a value, read with its get accessor, and addStubPropertyChange sets
    the next; addStubWriteDone writes a record when the stub answers, and
    startsWith matches an argument's start. setEASYQAMode has no effect."""
    run = utf_build(
        compiler,
        'chained.tut',
        'SAMPLE.STEPS.b',
        'SAMPLE.STATE.b',
        'SAMPLE.STATE.SET.b',
        stub_missing=True,
    )
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 2 checks in 1 runs\n')


def test_utf_recorded_stubs_dates_and_stopping(compiler):
    """setDate and setTime fix DATE() and TIME(); addEasyQAStub builds a stub from in and out
    matrices; addStubCommonCondition checks a COMMON variable; a stub
    marked setStopping ends the target's run, and runTest returns."""
    run = utf_build(compiler, 'recorded.tut', 'SAMPLE.RECORDED.b', stub_missing=True)
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 8 checks in 1 runs\n')


def test_utf_stub_named_after_the_implementing_routine(compiler):
    """utf_routines maps a component method, as calls name it, to the
    routine implementing it: a stub of either name answers."""
    run = utf_build(
        compiler,
        'routine-stub.tut',
        'SAMPLE.VIA.b',
        stub_missing=True,
        utf_routines={'sample.access.fetch': 'SAMPLE.FETCH.ROUTINE'},
    )
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 3 checks in 1 runs\n')


def test_utf_records_answer_data_access(compiler):
    """setRecord seeds records that unstubbed F.READ, CACHE.READ and
    component table reads return; F.WRITE stores one that getRecord reads
    back. F.SAMPLE and FBNK.SAMPLE name the same file."""
    run = utf_build(
        compiler,
        'records.tut',
        'SAMPLE.LOAD.b',
        stub_missing=True,
        utf_tables={'sample.records.sample': 'SAMPLE'},
    )
    assert (run.returncode, run.stderr) == (0, b'UTF: passed 5 checks in 1 runs\n')


def test_run_tuts_synthesizes_property_accessors(monkeypatch):
    """A component property bound to an insert's variable gets get, set
    and clear accessors, with indices for a matrix."""
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    import run_tuts
    from t24_components import property_bindings

    component = (
        "public property readwrite Today : string {\n    jBC: I_SAMPLE ->TODAY\n}\n"
        "public property readonly Rows : string {\njBC: I_SAMPLE ->ROWS()\n}\n"
    )
    bindings = dict(property_bindings(component))
    assert bindings == {
        'getToday': ('get', 'I_SAMPLE', 'TODAY', 0),
        'setToday': ('set', 'I_SAMPLE', 'TODAY', 0),
        'clearToday': ('clear', 'I_SAMPLE', 'TODAY', 0),
        'getRows': ('get', 'I_SAMPLE', 'ROWS', 1),
        'getDynArrayFromRows': ('getDynArrayFrom', 'I_SAMPLE', 'ROWS', 1),
    }
    assert run_tuts.accessor_source('x.settoday', bindings['setToday']) == (
        'SUBROUTINE x.settoday(VALUE)\n$INSERT I_COMMON\n$INSERT I_EQUATE\n$INSERT I_SAMPLE\n'
        'TODAY = VALUE\nRETURN\nEND\n'
    )
    assert run_tuts.accessor_source('x.getrows', bindings['getRows']) == (
        'FUNCTION x.getrows(I1)\n$INSERT I_COMMON\n$INSERT I_EQUATE\n$INSERT I_SAMPLE\n'
        'RETURN ROWS(I1)\nEND\n'
    )


def test_utf_without_its_target(compiler):
    """A target that isn't linked fails the test at runTest."""
    run = compiler.run_native(TESTCASES / 'twice.tut')
    assert run.returncode == 3
    assert b"target 'SAMPLE.TWICE' is not a routine of the program" in run.stderr


def test_run_tuts_finds_the_target(monkeypatch):
    """tools/run_tuts.py takes the target from a literal, or from a
    variable assigned one literal, with CRLF line ends."""
    monkeypatch.syspath_prepend(str(ROOT / 'tools'))
    import run_tuts

    assert run_tuts.test_target(b'UTF.setTarget("A.B")\r\n') == 'A.B'
    assert run_tuts.test_target(b'N = "X.Y"\r\n  UTF.setTarget(N)\r\n') == 'X.Y'
    assert run_tuts.test_target(b'N = "X"\nN = "Y"\nUTF.setTarget(N)\n') is None


def test_long_string_literals_split_for_c99(compiler):
    """A literal longer than C99's 4,095-byte limit is joined from pieces."""
    source = compiler.work / 'long.b'
    source.write_text("X = '" + 'ab' * 3000 + "'\nCRT LEN(X), X[5999, 2]\n")
    run = compiler.run_native(source)
    assert (run.returncode, run.stdout) == (0, b'6000\tab\n'), run.stderr
