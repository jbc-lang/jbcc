from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from compiler_support import NativeCompiler
from precompiled_runtime import PrecompiledRuntime, prepare_runtime

_RUNTIME_PATH = pytest.StashKey()


def pytest_addoption(parser):
    parser.addoption(
        '--embedded-runtime',
        action='store_true',
        help='compile the embedded runtime for every native test build',
    )


def _prepare_runtime(config):
    if config.getoption('--embedded-runtime'):
        return None
    directory = TemporaryDirectory(prefix='jbcc-test-runtime-')
    config.add_cleanup(directory.cleanup)
    return directory.name if prepare_runtime(Path(directory.name)) else None


@pytest.hookimpl(optionalhook=True)
def pytest_configure_node(node):
    # The xdist controller creates one object and keeps it alive for all workers.
    config = node.config
    if _RUNTIME_PATH not in config.stash:
        config.stash[_RUNTIME_PATH] = _prepare_runtime(config)
    node.workerinput['jbcc_runtime'] = config.stash[_RUNTIME_PATH]


@pytest.fixture(scope='session')
def precompiled_runtime(pytestconfig):
    if hasattr(pytestconfig, 'workerinput'):
        location = pytestconfig.workerinput['jbcc_runtime']
    else:
        location = _prepare_runtime(pytestconfig)
    return PrecompiledRuntime(location) if location is not None else None


@pytest.fixture
def compiler(tmp_path, precompiled_runtime):
    return NativeCompiler(tmp_path, precompiled_runtime)
