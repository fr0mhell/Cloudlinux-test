import argparse
import datetime as dt
from pathlib import Path
import subprocess

from differ import parse_diff, Diff, apply_diffs, process_logs, Status


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
    parser = argparse.ArgumentParser(
        prog='Conflict Resolver',
        description='Backports changes into new file trying to resolve conflicts.',
    )
    parser.add_argument('before')
    parser.add_argument('after')
    parser.add_argument('target')
    args = parser.parse_args()

    before = args.before  # 'examples/2_master'
    before_path = Path(before)
    if not before_path.exists():
        raise FileNotFoundError(f'File {before} not found')
    if not before_path.is_file():
        raise FileNotFoundError(f'{before} is not a file')

    after = args.after  # 'examples/1_branch'
    after_path = Path(after)
    if not after_path.exists():
        raise FileNotFoundError(f'File {after} not found')
    if not after_path.is_file():
        raise FileNotFoundError(f'{after} is not a file')
    result = 'result.c'

    before_lines = rawgencount(before)
    after_lines = rawgencount(after)

    diff_file = get_diff_file(before, after)
    diffs: list[Diff] = parse_diff(diff_file)
    Path(diff_file).unlink()
    logs = apply_diffs(before, diffs, result)

    with open(f'{dt.datetime.now().strftime("%Y%m%d_%H%M%S")}.log', 'w') as log_f:
        for log in process_logs(logs, before_lines, after_lines):
            if log.status == Status.ADDED:
                log_f.write(
                    f'{log.status}. {after} ({log.new_start}, {log.new_end}) -> '
                    f'{before} ({log.old_end})\n'
                )
            elif log.status == Status.REMOVED:
                log_f.write(
                    f'{log.status}. {after} ({log.new_start}) -x '
                    f'{before} ({log.old_start}, {log.old_end})\n'
                )
            else:
                log_f.write(
                    f'{log.status}. {after} ({log.new_start}, {log.new_end}) -> '
                    f'{before} ({log.old_start}, {log.old_end})\n'
                )

