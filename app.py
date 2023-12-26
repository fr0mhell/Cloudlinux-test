from pathlib import Path
import datetime as dt
import subprocess

from differ import parse_diff, Diff, apply_diffs


def _make_gen(reader):
    b = reader(1024 * 1024)
    while b:
        yield b
        b = reader(1024 * 1024)


def rawgencount(filename):
    f = open(filename, 'rb')
    f_gen = _make_gen(f.raw.read)
    return sum(buf.count(b'\n') for buf in f_gen)


def get_diff_file(before_file: str | Path, after_file: str | Path) -> str:
    """Get output from git diff command and save it to file."""
    if not Path(before_file).exists():
        raise FileNotFoundError(f'File {before_file} not found')
    if not Path(after_file).exists():
        raise FileNotFoundError(f'File {after_file} not found')

    diff_file_name = (
        f'{Path(before_file).stem}_{Path(after_file).stem}_'
        f'{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.diff'
    )
    with open(diff_file_name, 'w') as f:
        subprocess.run(['git', 'diff', '--no-index', before_file, after_file], stdout=f)
    return diff_file_name


if __name__ == '__main__':
    before = 'examples/2_master'
    after = 'examples/1_branch'
    result = 'result.c'

    before_lines = rawgencount(before)
    after_lines = rawgencount(after)

    diff_file = get_diff_file(before, after)
    diffs: list[Diff] = parse_diff(diff_file)
    logs = apply_diffs(before, diffs, result)
    print(logs)

