from dataclasses import dataclass, field
import re
import subprocess

before = 'examples/2_master'
after = 'examples/1_branch'
diff_file = 'examples/diff.txt'

diff_header = r'^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*'

with open(diff_file, 'w') as f:
    subprocess.run(['git', 'diff', '--no-index', before, after], stdout=f)


@dataclass
class Diff:
    old_start: int
    old_end: int

    new_start: int
    new_end: int

    lines: list[str] = field(default_factory=list)

    def process_diff(self):
        print(f'Processing diff {self.old_start} - {self.old_end}')

        resolved_content = []

        to_remove = []
        to_add = []

        old_counter = self.old_start
        new_counter = self.new_start

        for line in self.lines:
            if line.startswith('-'):
                to_remove.append(line.lstrip('-').strip())
                old_counter += 1

            if line.startswith('+'):
                to_add.append(line.lstrip('+').strip())
                new_counter += 1

            if line.startswith(' '):
                if to_add and to_remove:
                    entry = (
                        'Merge conflict. '
                        f'Old content: {old_counter - len(to_remove)}, {old_counter - 1}. '
                        f'New Content: {new_counter - len(to_add)}, {new_counter - 1}.'
                    )
                    print(entry)
                    resolved_content.extend(to_remove)
                    to_add, to_remove = [], []
                if to_add:
                    resolved_content.extend(to_add)
                    to_add = []
                if to_remove:
                    'remove old content'
                    to_remove = []

                resolved_content.append(line.strip())
                old_counter += 1
                new_counter += 1

        print('Done')


def parse_diff(diff_file: str) -> list[Diff]:
    # Parse diff file and collect all diffs
    with open(diff_file) as f:
        diffs: list[Diff] = []
        current_diff: Diff | None = None

        for idx, line in enumerate(f):
            # Skip first 4 lines of `git diff` output
            if idx < 4:
                continue

            if line.startswith('@@'):
                print(f'A difference found: {line}')

                if current_diff:
                    current_diff.process_diff()
                    diffs.append(current_diff)

                m = re.match(diff_header, line)
                old_diff_start, old_diff_size = int(m.group(1)), int(m.group(2))
                new_diff_start, new_diff_size = int(m.group(3)), int(m.group(4))
                current_diff = Diff(
                    old_start=old_diff_start,
                    old_end=old_diff_start + old_diff_size - 1,
                    new_start=new_diff_start,
                    new_end=new_diff_start + new_diff_size - 1,
                )
                continue

            current_diff.lines.append(line)

        current_diff.process_diff()
        diffs.append(current_diff)

    return diffs


parse_diff(diff_file)


