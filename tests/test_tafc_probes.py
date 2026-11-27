"""jbcc against the output TAFC PB201214 printed for each probe in tests/tafc.

The recorded output comes from `just tafc-probe --record` (observed reference
runs; TAFC-CROSSCHECK.md). This test needs no Docker: it builds each probe
with jbcc, under the emulation and jbcc options the probe names, and compares
its stdout with TAFC's, without the warnings TAFC prints on stdout.
"""

import importlib.util
import os
import subprocess

import pytest
from compiler_support import CLI, ROOT

spec = importlib.util.spec_from_file_location(
    'crosscheck', ROOT / 'tools/tafc_crosscheck/crosscheck.py'
)
assert spec is not None and spec.loader is not None
crosscheck = importlib.util.module_from_spec(spec)
spec.loader.exec_module(crosscheck)

PROBES = sorted((ROOT / 'tests/tafc').glob('*.b'))

# Differences kept on purpose; LANGUAGE-GAPS.md gives the reasons.
KNOWN_DIFFERENCES = {
    'at-tty.b': "jbcc keeps 'phantom', which T24 tests for",
    'char-bytes.b': 'strings cannot hold NUL bytes yet',
    'comparison-chains.b': 'jbcc keeps spaced comparison chains',
    'unassigned-continues.b': 'jbcc rejects provably unassigned reads',
}


@pytest.mark.parametrize('probe', PROBES, ids=[p.name for p in PROBES])
def test_probe_matches_tafc(compiler, probe):
    if probe.name in KNOWN_DIFFERENCES:
        pytest.skip(KNOWN_DIFFERENCES[probe.name])
    data = probe.read_bytes()
    options = crosscheck.OPTIONS_RE.search(data)
    extra = options.group(1).decode().split() if options else []
    emulation = crosscheck.emulation_of(data)
    main, companions = crosscheck.split_programs(data)
    for name, source in companions:
        (compiler.work / (name + '.b')).write_bytes(source)
        subprocess.run(
            [
                CLI,
                '--emulation',
                emulation,
                *extra,
                '--exe',
                name + '.b',
                '-o',
                name,
            ],
            cwd=compiler.work,
            check=True,
        )
    source = compiler.work / probe.name
    source.write_bytes(main)
    binary = compiler.work / 'probe'
    subprocess.run(
        [
            CLI,
            '--emulation',
            emulation,
            *extra,
            '--exe',
            source,
            '-o',
            binary,
        ],
        check=True,
    )
    env = {k: v for k, v in os.environ.items() if k not in ('COLUMNS', 'LINES')}
    env['TERM'] = 'vt100'
    run = subprocess.run(
        [binary],
        cwd=compiler.work,
        env=env,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        timeout=30,
    )
    expected = crosscheck.without_tafc_warnings(
        crosscheck.normalize(probe.with_suffix('.tafc.stdout').read_bytes())
    )
    assert crosscheck.normalize(run.stdout) == expected
