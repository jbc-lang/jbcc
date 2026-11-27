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
    binary = compiler.work / 'probe'
    subprocess.run(
        [
            CLI,
            '--emulation',
            crosscheck.emulation_of(data),
            *(options.group(1).decode().split() if options else []),
            '--exe',
            probe,
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
