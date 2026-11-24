import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / 'jbcc'


def expected_bytes(name):
    return (ROOT / 'tests/expected' / name).read_bytes()


def expected_text(name, **fields):
    text = expected_bytes(name).decode('utf-8')
    return text.format(**fields) if fields else text


class NativeCompiler:
    def __init__(self, work):
        self.work = work
        self.c = work / 'generated.c'

    def run_native(self, *sources, options=(), env=None, cwd=None):
        subprocess.run([CLI, *options, *sources, '-o', self.c], check=True)
        binary = self.work / 'program'
        subprocess.run(
            [
                'cc',
                '-std=c99',
                '-Wall',
                '-Wextra',
                '-Werror',
                '-pedantic',
                self.c,
                '-lm',
                '-o',
                binary,
            ],
            check=True,
        )
        return subprocess.run(
            [binary], capture_output=True, timeout=5, env=env, cwd=cwd
        )
