import pytest

from compiler_support import ROOT


@pytest.mark.parametrize('source', sorted((ROOT / 'tests/snippets').glob('*.b')),
                         ids=lambda source: source.name)
def test_snippet(compiler, source):
    run = compiler.run_native(source)
    assert run.returncode == 0, run.stderr
    assert run.stdout == source.with_suffix('.stdout').read_bytes()
    assert run.stderr == b''
