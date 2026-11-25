import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'jbcc'
C_FLAGS = ['-std=c99', '-Wall', '-Wextra', '-Werror', '-pedantic']


def expected_bytes(name):
    return (ROOT / 'tests/expected' / name).read_bytes()


def expected_text(name, **fields):
    text = expected_bytes(name).decode('utf-8')
    return text.format(**fields) if fields else text


class NativeCompiler:
    def __init__(self, work, runtime):
        self.work = work
        self.runtime = runtime
        self.c = work / 'generated.c'

    def run_native(self, *sources, options=(), env=None, cwd=None):
        subprocess.run([CLI, *options, *sources, '-o', self.c], check=True)
        binary = self.work / 'program'
        inputs = (
            self.runtime.compiler_inputs(self.c) if self.runtime else [self.c]
        )
        subprocess.run(
            ['cc', *C_FLAGS, *inputs, '-lm', '-o', binary], check=True
        )
        return subprocess.run(
            [binary], capture_output=True, timeout=5, env=env, cwd=cwd
        )
