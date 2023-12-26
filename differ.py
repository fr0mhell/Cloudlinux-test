from dataclasses import dataclass, field
import re

diff_header = r'^@@ -(\d+),(\d+) \+(\d+),(\d+) @@.*'


class Status:
    """Represents a status of merging content of two files."""
    CONFLICT = 'conflict'
    ADDED = 'added'
    REMOVED = 'removed'
    NO_CHANGE = 'no change'


@dataclass
class ResultLog:
    """Log entry with result of merging content of two files."""
    status: str
    old_start: int | None = None
    old_end: int | None = None
    new_start: int | None = None
    new_end: int | None = None


@dataclass
class Diff:
    """Represents a single diff obtained from `git diff` command."""
    old_start: int
    old_end: int

    new_start: int
    new_end: int

    lines: list[str] = field(default_factory=list)
    resolved_content: list[str] = field(default_factory=list)

    def process_diff(self) -> list[ResultLog]:
        """Process diff to add new content, remove old content or detect conflicts."""
        log_entries: list[ResultLog] = []

        to_remove = []
        to_add = []

        old_counter = self.old_start
        new_counter = self.new_start

        for line in self.lines:
            if line.startswith('-'):
                to_remove.append(line.lstrip('-').rstrip())
                old_counter += 1

            if line.startswith('+'):
                to_add.append(line.lstrip('+').rstrip())
                new_counter += 1

            if line.startswith(' '):

                if to_add and to_remove:
                    log_entries.append(ResultLog(
                        status=Status.CONFLICT,
                        old_start=old_counter - len(to_remove),
                        old_end=old_counter - 1,
                        new_start=new_counter - len(to_add),
                        new_end=new_counter - 1,
                    ))
                    # In case of conflict we need to add lines from old version
                    self.resolved_content.extend(to_remove)
                    to_add, to_remove = [], []
                elif to_add:
                    log_entries.append(ResultLog(
                        status=Status.ADDED,
                        old_end=old_counter - 1,
                        new_start=new_counter - len(to_add),
                        new_end=new_counter - 1,
                    ))
                    self.resolved_content.extend(to_add)
                    to_add = []
                elif to_remove:
                    log_entries.append(ResultLog(
                        status=Status.REMOVED,
                        old_start=old_counter - len(to_remove),
                        new_start=new_counter - len(to_add),
                        old_end=old_counter - 1,
                    ))
                    to_remove = []

                log_entries.append(ResultLog(
                    status=Status.NO_CHANGE,
                    old_start=old_counter,
                    old_end=old_counter,
                    new_start=new_counter,
                    new_end=new_counter,
                ))
                self.resolved_content.append(line.lstrip(' ').rstrip())
                old_counter += 1
                new_counter += 1

        print('Done\n')
        return log_entries


def parse_diff(diff_file: str) -> list[Diff]:
    """Parse diff file and collect all diffs."""
    with open(diff_file) as f:
        diffs: list[Diff] = []
        current_diff: Diff | None = None

        for idx, line in enumerate(f):
            # Skip first 4 lines of `git diff` output
            if idx < 4:
                continue

            if line.startswith('@@'):

                if current_diff:
                    diffs.append(current_diff)

                print(f'A difference found: {line}')

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

        diffs.append(current_diff)

    return diffs


def apply_diffs(before_file: str, diffs: list[Diff], result_file: str) -> list[ResultLog]:
    """Apply all diffs to add new content, remove old content or detect conflicts.

    If a conflict detected, the old content will be added to the result file and a log entry will
    be created.

    """
    log_entries = []

    with open(result_file, 'w') as res_f:

        with open(before_file) as before_f:
            current_diff = 0

            for idx, line in enumerate(before_f, start=1):
                if current_diff >= len(diffs):
                    res_f.write(line)
                    continue

                if idx < diffs[current_diff].old_start:
                    res_f.write(line)
                    continue

                if diffs[current_diff].old_start == idx:
                    log_entries.extend(diffs[current_diff].process_diff())

                if idx == diffs[current_diff].old_end:
                    res_f.writelines(f'{l}\n' for l in diffs[current_diff].resolved_content)
                    current_diff += 1
                    continue

    return log_entries


def process_logs(logs: list[ResultLog], old_file_length: int, new_file_length: int):
    no_changes = []
    for idx, log in enumerate(logs):
        if idx == 0 and log.old_start and log.old_start > 1:
            no_changes.append(ResultLog(
                status=Status.NO_CHANGE,
                old_start=1,
                old_end=log.old_start - 1,
                new_start=1,
                new_end=log.new_start - 1,
            ))

        if log.status in {Status.ADDED, Status.REMOVED, Status.CONFLICT}:
            if no_changes:
                yield ResultLog(
                    status=Status.NO_CHANGE,
                    old_start=no_changes[0].old_start,
                    old_end=no_changes[-1].old_end,
                    new_start=no_changes[0].new_start,
                    new_end=no_changes[-1].new_end,
                )
                no_changes = []
            yield log
        else:
            no_changes.append(log)

        if idx == len(logs) - 1:
            no_changes.append(ResultLog(
                status=Status.NO_CHANGE,
                old_start=log.old_end + 1,
                old_end=old_file_length,
                new_start=log.new_end + 1,
                new_end=new_file_length,
            ))

    if no_changes:
        yield ResultLog(
            status=Status.NO_CHANGE,
            old_start=no_changes[0].old_start,
            old_end=no_changes[-1].old_end,
            new_start=no_changes[0].new_start,
            new_end=no_changes[-1].new_end,
        )
