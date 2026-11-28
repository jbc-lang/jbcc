import re
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

    def run_native(self, *sources, options=(), env=None, cwd=None, stdin=None):
        subprocess.run([CLI, *options, *sources, '-o', self.c], check=True)
        binary = self.work / 'program'
        inputs = (
            self.runtime.compiler_inputs(self.c) if self.runtime else [self.c]
        )
        subprocess.run(
            ['cc', *C_FLAGS, *inputs, '-lm', '-o', binary], check=True
        )
        return subprocess.run(
            [binary],
            input=stdin,
            capture_output=True,
            timeout=5,
            env=env,
            cwd=cwd,
        )


def unassigned_warning(expected):
    """The warning a runtime unassigned read gives, from the text of the
    fatal error it replaced: jbcc warns, uses '' and continues, as TAFC
    PB201214 does (TAFC-CROSSCHECK.md section 3)."""
    return re.sub(
        r": unassigned variable ('[^']*')$",
        r": warning: unassigned variable \1 -- NULL USED",
        expected,
        flags=re.MULTILINE,
    )


def assert_unassigned_warning(run, expected):
    """The program warned about an unassigned read and went on."""
    stderr = run.stderr if isinstance(run.stderr, str) else run.stderr.decode()
    assert run.returncode == 0, stderr
    assert unassigned_warning(expected) in stderr


def assert_run_matches(run, expected):
    """Compare (returncode, stdout, stderr) with expected, except that an
    expected fatal unassigned read is now a warning after which the program
    goes on (see unassigned_warning)."""
    code, _, stderr = expected
    text = stderr if isinstance(stderr, str) else stderr.decode()
    if code == 1 and re.search(r": unassigned variable '[^']*'$", text, re.M):
        assert_unassigned_warning(run, text)
    else:
        assert (run.returncode, run.stdout, run.stderr) == expected
