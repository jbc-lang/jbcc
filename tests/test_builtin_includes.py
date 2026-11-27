import subprocess
import sys
from pathlib import Path

from compiler_support import CLI, ROOT

SOURCE = ROOT / 'tests/includes/uses-jbc-h.b'
NOTE = "note: using jbcc's built-in JBC.h"


def test_builtin_jbc_h_is_used_when_none_is_found(compiler):
    binary = compiler.work / 'program'
    build = subprocess.run(
        [CLI, '--exe', SOURCE, '-o', binary], capture_output=True, text=True
    )
    assert build.returncode == 0, build.stderr
    assert NOTE in build.stderr
    assert subprocess.check_output([binary]) == b'1\t10\t5\t/\n'


def test_jbc_h_on_the_include_path_wins(compiler):
    binary = compiler.work / 'program'
    build = subprocess.run(
        [CLI, '--exe', SOURCE, '-I', ROOT / 'tests/includes/own', '-o', binary],
        capture_output=True,
        text=True,
    )
    assert build.returncode != 0
    assert NOTE not in build.stderr
    assert "unknown variable or unsupported function 'JIOCTL_COMMAND_FILESTATUS'" in build.stderr


def test_no_builtin_includes_reports_the_missing_header(compiler):
    build = subprocess.run(
        [CLI, SOURCE, '--no-builtin-includes', '-o', compiler.work / 'program.c'],
        capture_output=True,
        text=True,
    )
    assert build.returncode != 0
    assert f"{SOURCE}:2:1: include file 'JBC.h' not found" in build.stderr


def test_browser_translation_uses_the_builtin_jbc_h(tmp_path):
    (tmp_path / 'main.b').write_bytes(SOURCE.read_bytes())
    script = (
        'from pathlib import Path\n'
        'from jbcc.browser import translate\n'
        "c = translate([Path('main.b')], include_resolver=lambda *_: None)\n"
        "print('JIOCTL' not in c and 'jbc_' in c)\n"
    )
    run = subprocess.run(
        [sys.executable, '-c', script],
        cwd=tmp_path,
        env={'PYTHONPATH': str(ROOT / 'src')},
        capture_output=True,
        text=True,
    )
    assert run.returncode == 0, run.stderr
    assert run.stdout == 'True\n'
    assert NOTE in run.stderr
