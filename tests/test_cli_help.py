import re
import subprocess
import sys

from compiler_support import CLI, ROOT


def help_text(command):
    run = subprocess.run(
        [*command, '--help'], capture_output=True, text=True, check=True
    )
    return run.stdout


def options_in_usage(text):
    usage = text.split('\n\n', 1)[0]
    return set(re.findall(r'\[(-{1,2}[\w-]+)', usage))


def described(text, option):
    # Each option sits on its own line with an indented description below.
    return re.search(rf'^  {re.escape(option)}\b.*\n {{8}}\S', text, re.M)


def test_jbcc_help_describes_every_option():
    text = help_text([CLI])
    for heading in ('input:', 'output and build:', 'diagnostics:', 'environment:'):
        assert f'\n{heading}\n' in text
    options = options_in_usage(text) - {'-h'}
    assert {'-I', '-o', '--exe', '--run', '--no-builtin-includes'} <= options
    for option in options:
        assert described(text, option), option


def test_check_corpus_help_describes_every_option():
    text = help_text([sys.executable, ROOT / 'tools/check_corpus.py'])
    for heading in (
        'general:',
        'T24 source handling:',
        'T24 selection and exclusion:',
        'T24 R19 components:',
        'T24 testing stubs:',
        'T24 flags:',
    ):
        assert f'\n{heading}\n' in text
    options = options_in_usage(text) - {'-h'}
    assert {'--t24-stub-members', '--t24-relax-access', '-I'} <= options
    for option in options:
        assert described(text, option), option
