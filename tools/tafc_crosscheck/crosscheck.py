"""Run jBC programs through jbcc and the TAFC reference runtime and compare.

The reference runtime is TAFC PB201214 in the Docker image that
../jbc-internals/docker builds. See TAFC-CROSSCHECK.md for the setup and
README.md ("Cross-check with TAFC") for the commands.

  guide     every code block of the jBC guide, classified
  probe     the given probe files or directories, side by side; --record
            saves TAFC's stdout as NAME.tafc.stdout next to each probe
  recorded  jbcc against the saved NAME.tafc.stdout files (no Docker)

Standard library only.
"""

import argparse
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
JBCC = ROOT / 'jbcc'
CACHE = ROOT / '.cache' / 'tafc'
INTERNALS = ROOT.parent / 'jbc-internals'
TARBALL = INTERNALS / 'TAFC_PB201214_LINUX_ELF_AS6_106034-unbound.tar.gz'
DOCKER_DIR = INTERNALS / 'docker'
IMAGE = 'jbc-internals-tafc-runner:local'
GUIDE = ROOT.parent / 'jbc-language'
RUN_SECONDS = 10
NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9._-]*$')

# A probe selects its emulation with a comment line near the top, for
# example "* tafc-emulation: jbase". The default is prime, as in T24.
EMULATION_RE = re.compile(rb'^\s*[*!]\s*tafc-emulation:\s*(\w+)', re.M)

# Output of these depends on the clock, the process, random numbers or the
# directory, so a difference does not show a semantic mismatch.
VOLATILE_RE = re.compile(
    r'\b(TIME|DATE|TIMEDATE|TIMESTAMP|MAKETIMESTAMP|LOCALDATE|LOCALTIME|RND'
    r'|UNIQUEKEY|GETCWD|SYSTEM\s*\(\s*(12|1000|1001|1007|1019|1031|1034))\b'
    r'|@(PID|PATH|TIME|DATE|DAY|MONTH|YEAR|USERNO|TTY|UID)\b',
    re.I,
)


# TAFC prints its runtime warnings on stdout, each followed by a location
# line; jbcc prints its warnings on stderr. The comparison drops TAFC's.
TAFC_WARNING_RE = re.compile(
    r'^(Non-numeric value -- ZERO USED ,|Invalid or uninitialised variable'
    r' -- NULL USED ,|Divide by zero !!|Unknown conversion code\.)\n'
    r'(Var(iable)? .*\n|Line +\d+ , Source .*\n)?',
    re.M,
)


def without_tafc_warnings(text):
    return TAFC_WARNING_RE.sub('', text + '\n').rstrip('\n')


def read(path):
    return path.read_bytes() if path.exists() else None


def normalize(data):
    """Text for comparison: no CR, no trailing spaces, no blank edges."""
    text = (data or b'').decode('utf-8', 'replace').replace('\r', '')
    return '\n'.join(line.rstrip() for line in text.split('\n')).strip('\n')


def ensure_image(docker_dir):
    found = subprocess.run(
        ['docker', 'image', 'inspect', IMAGE], capture_output=True
    )
    if found.returncode:
        print('Building %s from %s' % (IMAGE, docker_dir), file=sys.stderr)
        subprocess.run(
            [
                'docker',
                'build',
                '--platform',
                'linux/amd64',
                '--tag',
                IMAGE,
                str(docker_dir),
            ],
            check=True,
        )


def run_tafc(probes, output, args, emulation):
    """Compile and run every probes/*.b with TAFC into output/."""
    output.mkdir(parents=True, exist_ok=True)
    mounts = [
        (args.tarball, '/input/tafc.tar.gz', True),
        (HERE / 'container.sh', '/harness/container.sh', True),
        (probes, '/probes', True),
        (output, '/output', False),
    ]
    command = [
        'docker',
        'run',
        '--rm',
        '--pull=never',
        '--network',
        'none',
        '--platform',
        'linux/amd64',
        '--entrypoint',
        'bash',
        '-e',
        'JOBS=%d' % args.tafc_jobs,
        '-e',
        'EMU=' + emulation,
        '-e',
        'RUN_SECONDS=%d' % RUN_SECONDS,
    ]
    for source, target, readonly in mounts:
        spec = 'type=bind,"source=%s",target=%s' % (
            str(Path(source).resolve()).replace('"', '""'),
            target,
        )
        command += ['--mount', spec + (',readonly' if readonly else '')]
    command += [IMAGE, '/harness/container.sh']
    done = subprocess.run(command, capture_output=True, text=True)
    if done.returncode:
        sys.exit('TAFC container failed:\n' + done.stdout + done.stderr)


def emulation_of(data):
    match = EMULATION_RE.search(data)
    return match.group(1).decode() if match else 'prime'


def run_jbcc_one(source, output, emulation):
    name = source.stem
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        shutil.copy(source, work / source.name)
        program = work / name
        built = subprocess.run(
            [
                sys.executable,
                str(JBCC),
                '--emulation',
                emulation,
                '--exe',
                source.name,
                '-o',
                name,
            ],
            cwd=work,
            capture_output=True,
            timeout=300,
        )
        (output / (name + '.clog')).write_bytes(built.stdout + built.stderr)
        (output / (name + '.crc')).write_text('%d\n' % built.returncode)
        if built.returncode or not program.exists():
            return
        try:
            ran = subprocess.run(
                [str(program)],
                cwd=work,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                timeout=RUN_SECONDS,
            )
            out, err, status = ran.stdout, ran.stderr, ran.returncode
        except subprocess.TimeoutExpired as expired:
            out, err, status = expired.stdout or b'', expired.stderr or b'', 124
        (output / (name + '.out')).write_bytes(out)
        (output / (name + '.err')).write_bytes(err)
        (output / (name + '.rc')).write_text('%d\n' % status)


def run_jbcc(probes, output, jobs, emulation=None):
    """Build and run every probes/*.b with jbcc; without an emulation, each
    probe's own tafc-emulation comment decides."""
    output.mkdir(parents=True, exist_ok=True)
    sources = sorted(probes.glob('*.b'))

    def one(source):
        chosen = emulation or emulation_of(source.read_bytes())
        run_jbcc_one(source, output, chosen)

    with ThreadPoolExecutor(jobs) as pool:
        list(pool.map(one, sources))


def side(directory, name):
    def number(ext):
        data = read(directory / (name + ext))
        return int(data) if data else None

    return {
        'compile_status': number('.crc'),
        'compile_log': normalize(read(directory / (name + '.clog'))),
        'status': number('.rc'),
        'stdout': normalize(read(directory / (name + '.out'))),
        'stderr': normalize(read(directory / (name + '.err'))),
    }


def classify(tafc, jbcc):
    if tafc['compile_status'] != 0:
        return 'tafc-rejects'
    if tafc['status'] is None:
        return 'tafc-no-program'
    if jbcc['compile_status'] != 0:
        return 'jbcc-rejects'
    if jbcc['stdout'] == tafc['stdout']:
        return 'same'
    if jbcc['status'] != 0 and tafc['status'] == 0:
        return 'jbcc-fails'
    return 'differ'


def first_line(text):
    lines = [
        line
        for line in text.splitlines()
        if line.strip() and 'built-in JBC.h' not in line
    ]
    return re.sub(r'^\S+?:\d+:\d+: ', '', lines[0]) if lines else ''


def prepare(sources, work):
    """Copy (label, text, name) sources to work/<emulation>/probes/ and
    return {emulation: [(program name, label, text)]}. A source keeps its
    own program name when it is a usable, unique file name, because TAFC's
    runtime warnings and SYSTEM(40) show it; otherwise it becomes P0001,
    P0002 and so on."""
    groups = defaultdict(list)
    used = set()
    shutil.rmtree(work, ignore_errors=True)
    for number, (label, data, wanted) in enumerate(sources, 1):
        emulation = emulation_of(data)
        name = 'P%04d' % number
        if wanted and NAME_RE.match(wanted) and wanted.lower() not in used:
            name = wanted
        used.add(name.lower())
        directory = work / emulation / 'probes'
        directory.mkdir(parents=True, exist_ok=True)
        (directory / (name + '.b')).write_bytes(data)
        groups[emulation].append((name, label, data))
    return groups


def execute(groups, work, args):
    results = []
    for emulation, entries in sorted(groups.items()):
        base = work / emulation
        run_tafc(base / 'probes', base / 'tafc', args, emulation)
        run_jbcc(base / 'probes', base / 'jbcc', args.jobs, emulation)
        for name, label, data in entries:
            tafc = side(base / 'tafc', name)
            tafc['stdout'] = without_tafc_warnings(tafc['stdout'])
            jbcc = side(base / 'jbcc', name)
            source = data.decode('utf-8', 'replace')
            results.append(
                {
                    'program': name,
                    'source': label,
                    'emulation': emulation,
                    'category': classify(tafc, jbcc),
                    'volatile': bool(VOLATILE_RE.search(source)),
                    'code': source,
                    'tafc': tafc,
                    'jbcc': jbcc,
                }
            )
    return results


def summary(results):
    lines = []
    counts = Counter(row['category'] for row in results)
    volatile = sum(
        1 for row in results if row['category'] == 'differ' and row['volatile']
    )
    lines.append(
        'Totals: '
        + ', '.join(
            '%s %d' % (category, counts[category])
            for category in (
                'same',
                'differ',
                'jbcc-rejects',
                'jbcc-fails',
                'tafc-rejects',
                'tafc-no-program',
            )
            if counts[category]
        )
    )
    lines.append(
        'Differences that may come from the clock, process or '
        'random numbers: %d of %d' % (volatile, counts['differ'])
    )
    for category, field in (
        ('jbcc-rejects', 'compile_log'),
        ('jbcc-fails', 'stderr'),
    ):
        grouped = defaultdict(list)
        for row in results:
            if row['category'] == category:
                key = first_line(row['jbcc'][field]) or (
                    'status %s' % row['jbcc']['status']
                )
                grouped[key].append(row['source'])
        if grouped:
            lines += ['', '## %s, by jbcc diagnostic' % category]
            for key, sources in sorted(
                grouped.items(), key=lambda item: -len(item[1])
            ):
                lines.append(
                    '%3d  %s  [%s]'
                    % (len(sources), key[:100], ', '.join(sources[:4]))
                )
    lines += ['', '## differ']
    for row in results:
        if row['category'] != 'differ':
            continue
        lines.append(
            '### %s%s'
            % (row['source'], ' (volatile)' if row['volatile'] else '')
        )
        lines.append('--- tafc, status %s' % row['tafc']['status'])
        lines += row['tafc']['stdout'].splitlines()[:20]
        lines.append('--- jbcc, status %s' % row['jbcc']['status'])
        lines += row['jbcc']['stdout'].splitlines()[:20]
        if row['jbcc']['stderr']:
            lines.append(
                '    jbcc stderr: ' + first_line(row['jbcc']['stderr'])
            )
    return '\n'.join(lines) + '\n'


def write_report(results, out):
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(results, indent=1))
    text = summary(results)
    (out / 'report.txt').write_text(text)
    return text


def guide_sources(guide, site):
    """(label, code) for each unique guide code block with statements,
    read the way the guide's check_examples.py reads them."""
    spec = importlib.util.spec_from_file_location(
        'check_examples', guide / 'check_examples.py'
    )
    if spec is None or spec.loader is None:
        sys.exit('Cannot load %s/check_examples.py' % guide)
    examples = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(examples)
    subprocess.run(
        [sys.executable, str(guide / 'build.py'), '--out', str(site)],
        check=True,
        capture_output=True,
    )
    chapters = defaultdict(list)
    for chapter, code in examples.blocks(site):
        if examples.has_statements(code):
            chapters[code].append(chapter)
    return [
        ('%s#%s' % (names[0], examples.fnv1a(code)), code.encode(), None)
        for code, names in sorted(chapters.items(), key=lambda item: item[1][0])
    ]


def probe_files(paths):
    files = []
    for path in map(Path, paths):
        files += sorted(path.glob('*.b')) if path.is_dir() else [path]
    if not files:
        sys.exit('No .b files in ' + ' '.join(paths))
    return files


def show(results):
    for row in results:
        print(
            '################ %s  [%s, %s]'
            % (row['source'], row['category'], row['emulation'])
        )
        for name in ('tafc', 'jbcc'):
            result = row[name]
            if result['compile_status'] != 0:
                print(
                    '--- %s: compile status %s'
                    % (name, result['compile_status'])
                )
                print('\n'.join(result['compile_log'].splitlines()[:6]))
                continue
            print('--- %s: status %s' % (name, result['status']))
            if result['stdout']:
                print(result['stdout'])
            if result['stderr']:
                print(
                    '  [stderr] '
                    + '\n  '.join(result['stderr'].splitlines()[:6])
                )


def command_guide(args):
    site = CACHE / 'guide-site'
    sources = guide_sources(args.guide, site)
    work = CACHE / 'guide'
    groups = prepare(sources, work)
    results = execute(groups, work, args)
    print(write_report(results, work).split('\n## ')[0])
    print('Report: %s/report.txt and report.json' % work.relative_to(ROOT))


def command_probe(args):
    files = probe_files(args.paths)
    work = CACHE / 'probe'
    sources = [(str(path), path.read_bytes(), path.stem) for path in files]
    results = execute(prepare(sources, work), work, args)
    write_report(results, work)
    show(results)
    if args.record:
        for row in results:
            name = row['program']
            path = Path(row['source'])
            raw = read(work / row['emulation'] / 'tafc' / (name + '.out'))
            if raw is None:
                print('Not recorded (TAFC did not run it): %s' % path)
                continue
            path.with_suffix('.tafc.stdout').write_bytes(raw)
        print('Recorded TAFC stdout next to %d probes' % len(files))


def command_recorded(args):
    files = [
        path
        for path in probe_files(args.paths)
        if path.with_suffix('.tafc.stdout').exists()
    ]
    with tempfile.TemporaryDirectory() as work:
        work = Path(work)
        probes = work / 'probes'
        probes.mkdir()
        names = {}
        for number, path in enumerate(files, 1):
            name = path.stem
            if not NAME_RE.match(name) or (probes / (name + '.b')).exists():
                name = 'P%04d' % number
            shutil.copy(path, probes / (name + '.b'))
            names[name] = path
        run_jbcc(probes, work / 'jbcc', args.jobs)
        failed = 0
        for name, path in sorted(names.items()):
            expected = without_tafc_warnings(
                normalize(read(path.with_suffix('.tafc.stdout')))
            )
            jbcc = side(work / 'jbcc', name)
            if jbcc['compile_status'] == 0 and jbcc['stdout'] == expected:
                print('same    %s' % path)
                continue
            failed += 1
            reason = (
                first_line(jbcc['compile_log'])
                if jbcc['compile_status']
                else first_line(jbcc['stderr']) or 'different output'
            )
            print('differ  %s: %s' % (path, reason))
        print(
            '%d of %d probes match the recorded TAFC output'
            % (len(files) - failed, len(files))
        )
        return 1 if failed and args.strict else 0


def main():
    parser = argparse.ArgumentParser(
        description='Compare jbcc with the TAFC reference runtime.'
    )
    parser.add_argument('--tarball', type=Path, default=TARBALL)
    parser.add_argument('--docker-dir', type=Path, default=DOCKER_DIR)
    parser.add_argument(
        '--jobs',
        type=int,
        default=os.cpu_count() or 4,
        help='parallel jbcc builds',
    )
    parser.add_argument(
        '--tafc-jobs',
        type=int,
        default=2,
        help='parallel TAFC programs; more than 2 can fail '
        'on TAFC licensing or shared memory',
    )
    commands = parser.add_subparsers(dest='command', required=True)
    guide = commands.add_parser('guide', help='run every guide code block')
    guide.add_argument(
        '--guide',
        type=Path,
        default=GUIDE,
        help='jbc-language checkout (default ../jbc-language)',
    )
    probe = commands.add_parser('probe', help='run probes side by side')
    probe.add_argument('paths', nargs='+')
    probe.add_argument(
        '--record',
        action='store_true',
        help='save TAFC stdout as NAME.tafc.stdout',
    )
    recorded = commands.add_parser(
        'recorded', help='compare jbcc with recorded TAFC output'
    )
    recorded.add_argument('paths', nargs='+')
    recorded.add_argument(
        '--strict',
        action='store_true',
        help='exit with status 1 on any difference',
    )
    args = parser.parse_args()

    if args.command != 'recorded':
        if not args.tarball.is_file():
            sys.exit('TAFC tarball not found: %s' % args.tarball)
        ensure_image(args.docker_dir)
    handler = {
        'guide': command_guide,
        'probe': command_probe,
        'recorded': command_recorded,
    }[args.command]
    return handler(args)


if __name__ == '__main__':
    sys.exit(main())
