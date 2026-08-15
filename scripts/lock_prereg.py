#!/usr/bin/env python3
"""Lock the preregistration file.

Appends a UTC timestamp and the current git commit hash to the Lock section,
then commits the file. Refuses to run if the file is incomplete or already
locked.

Usage:
    python scripts/lock_prereg.py
    python scripts/lock_prereg.py --path prereg.md
    python scripts/lock_prereg.py --dry-run
"""

import argparse
import datetime
import re
import subprocess
import sys
from pathlib import Path

TIMESTAMP_FIELD = "Timestamp (UTC):"
COMMIT_FIELD = "Git commit hash:"
AUTHORS_FIELD = "Authors:"


def fail(message):
    print(f"REFUSED: {message}", file=sys.stderr)
    sys.exit(1)


def git(*args):
    """Run a git command and return stripped stdout."""
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        fail(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def field_value(text, field):
    """Return whatever follows a 'Field:' label on the same line."""
    match = re.search(rf"^{re.escape(field)}[ \t]*(.*)$", text, re.MULTILINE)
    if match is None:
        fail(f"could not find the line '{field}' in the file")
    return match.group(1).strip()


def check_not_locked(text):
    if field_value(text, TIMESTAMP_FIELD) or field_value(text, COMMIT_FIELD):
        fail(
            "this preregistration is already locked. "
            "Locking twice would defeat the purpose of the timestamp."
        )


def check_no_placeholders(text):
    """Square-bracket placeholders must be filled in before locking.

    Markdown links look like [text](url), so those are ignored.
    """
    placeholders = [
        match.group(0)
        for match in re.finditer(r"\[[^\]\n]+\](?!\()", text)
    ]
    if placeholders:
        listed = "\n  ".join(placeholders[:10])
        fail(f"unfilled placeholders remain:\n  {listed}")


def check_predictions_table(text):
    """The predictions table needs at least one real data row."""
    section = re.search(
        r"^##\s+Predictions\s*$(.*?)^##\s", text, re.MULTILINE | re.DOTALL
    )
    if section is None:
        fail("could not find a '## Predictions' section")

    rows = [
        line.strip()
        for line in section.group(1).splitlines()
        if line.strip().startswith("|")
    ]
    # Drop the header row and the |---|---| separator.
    data_rows = [
        row for row in rows[2:] if set(row.replace("|", "").strip()) not in (set(), {"-"})
    ]
    if not data_rows:
        fail("the predictions table is empty. Fill it in before locking.")
    return len(data_rows)


def check_authors(text):
    if not field_value(text, AUTHORS_FIELD):
        fail("the Authors field is empty. State who made these predictions.")


def check_clean_worktree(path):
    status = git("status", "--porcelain", str(path))
    if status:
        fail(
            f"{path} has uncommitted changes. Commit or discard them first, "
            "so the locked hash refers to a known state of the file."
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", default="prereg.md")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="run the checks and print what would be written, without writing.",
    )
    args = parser.parse_args()

    path = Path(args.path)
    if not path.exists():
        fail(f"{path} does not exist")

    text = path.read_text(encoding="utf-8")

    check_not_locked(text)
    check_no_placeholders(text)
    n_predictions = check_predictions_table(text)
    check_authors(text)
    check_clean_worktree(path)

    timestamp = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%d %H:%M:%S UTC"
    )
    commit = git("rev-parse", "HEAD")

    print(f"Checks passed. {n_predictions} prediction rows found.")
    print(f"Timestamp: {timestamp}")
    print(f"Commit:    {commit}")

    if args.dry_run:
        print("\nDry run. Nothing written.")
        return

    locked = text.replace(TIMESTAMP_FIELD, f"{TIMESTAMP_FIELD} {timestamp}", 1)
    locked = locked.replace(COMMIT_FIELD, f"{COMMIT_FIELD} {commit}", 1)
    path.write_text(locked, encoding="utf-8")

    git("add", str(path))
    git("commit", "-m", "lock preregistration")
    lock_commit = git("rev-parse", "HEAD")

    print(f"\nLocked. Lock commit: {lock_commit}")
    print("The referenced commit predates any data collection.")


if __name__ == "__main__":
    main()
