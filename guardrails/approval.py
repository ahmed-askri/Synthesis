from pathlib import Path


def cli_approve(report):
    print("\n" + report + "\n")
    return input("Save this report to reports/report.md? [y/N] ").strip().lower() == "y"


def save_with_approval(report, approve, path="reports/report.md"):
    """The only function that writes a report to disk. It runs only if a human says yes."""
    if not report.strip():
        return None
    if approve(report) is not True:  # only a literal True counts as approval
        return None
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(report, encoding="utf-8")
    return str(target)