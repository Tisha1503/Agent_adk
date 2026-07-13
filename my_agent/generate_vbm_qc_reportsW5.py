"""
Week 5 helper: generate example VBM QC reports.

Runs ``run_vbm_qc`` on the example subject folders and writes the Markdown
reports next to the repo root. Run from the repo root:

    python -m my_agent.generate_vbm_qc_reportsW5
"""

import os

from my_agent.vbm_qc_reasoner import run_vbm_qc

_TARGETS = [
    ("test_vbm_complete", "vbm_qc_report_complete.md"),
    ("test_vbm_problem", "vbm_qc_report_problem.md"),
    ("test_vbm_subject", "vbm_qc_report.md"),
]


def main():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for folder, out_name in _TARGETS:
        target = os.path.join(root, folder)
        result = run_vbm_qc(target)
        out_path = os.path.join(root, out_name)
        if result.get("status") == "error":
            print(f"[skip] {folder}: {result.get('message')}")
            continue
        with open(out_path, "w", encoding="utf-8") as fh:
            fh.write(result["markdown_report"])
        print(f"[ok] {folder}: {result['qc_status']} -> {out_name}")


if __name__ == "__main__":
    main()
