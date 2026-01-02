"""Report generation commands."""

import time

# Simulate expensive import (e.g., pandas, matplotlib)
print("[reports.py] Importing reports module... (simulating 1.5s delay)")
time.sleep(1.5)
print("[reports.py] Import complete!")


def generate(report_type: str, *, output: str = "report.pdf"):
    """Generate a business report.

    Parameters
    ----------
    report_type
        Type of report: 'sales', 'inventory', or 'financial'.
    output
        Output file path.
    """
    print(f"Generating {report_type} report -> {output}")


def schedule(report_type: str, cron: str):
    """Schedule recurring report generation.

    Parameters
    ----------
    report_type
        Type of report to schedule.
    cron
        Cron expression for schedule (e.g., '0 9 * * 1').
    """
    print(f"Scheduled {report_type} report with cron: {cron}")
