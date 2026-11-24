import pytest

from compiler_support import NativeCompiler


@pytest.fixture
def compiler(tmp_path):
    return NativeCompiler(tmp_path)
