# Week 5 - VBM Workflow Validation, QC Rules, and Remediation

Week 4 could detect how far the VBM pipeline had progressed and draft the next
step. Week 5 makes the agent *skeptical*: it validates whether the detected
state is internally consistent, applies a set of QC rules to catch common
SPM/CAT12 problems, classifies each subject, and explains — in beginner-friendly
language — what went wrong and what to do about it.

The guiding idea is the one from `CommonVBM_QC_issues.md`: a pipeline can finish
a step without throwing an error and still leave output that is wrong or
incomplete. The QC reasoner exists to catch those silent failures from the file
trail alone.

## What's new this week

1. **Inconsistency detection** in the state detector. Beyond "how far did we
   get", it now flags file combinations that cannot come from one clean run.
2. **A QC rule file** (`vbm_qc_rules.yaml`) holding the human-readable knowledge:
   issue, evidence, likely cause, severity, recommended action, and expected
   output after correction.
3. **A QC reasoner** (`vbm_qc_reasoner.py`) that reads the Week 4 state, applies
   the rules, classifies the subject as **READY / WARNING / INCOMPLETE / ERROR**,
   and produces warnings, recommendations, and a tutorial explanation.
4. **A Markdown QC report** generator, with example reports for a complete case
   and a problematic case.

## Files

| File | Purpose |
|---|---|
| `my_agent/vbm_qc_rules.yaml` | The QC rule knowledge base (issue / evidence / cause / severity / action / expected output). |
| `my_agent/vbm_qc_reasoner.py` | `reason_about_vbm_qc(state_report)` and `run_vbm_qc(folder_path)` — the QC engine and report formatter. |
| `my_agent/vbm_state_detectorW4.py` | Extended with `analyze_vbm_inconsistencies(files)` and new inconsistency fields. |
| `my_agent/agent.py` | Wires the two QC tools into the ADK agent. |
| `my_agent/generate_vbm_qc_reportsW5.py` | Helper that writes the example reports. |
| `vbm_qc_report.md` | QC report for the `test_vbm_subject` folder (WARNING case). |
| `vbm_qc_report_complete.md` | Example report — a complete, READY case. |
| `vbm_qc_report_problem.md` | Example report — an inconsistent, ERROR case. |
| `test_vbm_complete/` | Dummy subject with a full, consistent pipeline. |
| `test_vbm_problem/` | Dummy subject with partial segmentation + orphaned DARTEL flow field. |

## The four QC statuses

| Status | Meaning |
|---|---|
| `READY` | Pipeline complete and every prerequisite verified. Ready for statistics. |
| `WARNING` | Progressing correctly, but there is a QC caution worth checking (e.g. no deformation field, unverified intermediates). |
| `INCOMPLETE` | A normal in-progress state — more preprocessing steps remain, nothing wrong. |
| `ERROR` | The file set is inconsistent. Fix it before continuing. |

## Inconsistency checks

`analyze_vbm_inconsistencies(files)` returns a list of problems, each tied to a
stable rule id the reasoner matches on:

- **partial_segmentation** — `c1`/`p1` present but `c2`/`c3` (or `p2`/`p3`) missing.
- **flowfield_without_import** — a DARTEL flow field `u_rc1` with no `rc1`/`rc2`.
- **partial_dartel_subjects** — several subjects have imports but only some have
  flow fields (a group DARTEL run that didn't cover everyone).
- **smoothed_without_modulated** — `smwc1`/`smwp1` present but the modulated
  `mwc1`/`mwp1` inputs are missing.

The detector also still flags later-stage files with no segmentation at all.

## The QC rules

Each rule in `vbm_qc_rules.yaml` carries everything needed to explain a problem:

```yaml
- id: smoothed_without_modulated
  issue: "Smoothed maps without modulated inputs"
  evidence: "Smoothed maps (smwc1/smwp1) exist but the modulated maps (mwc1/mwp1) are missing."
  likely_cause: "Modulated inputs were deleted, or smoothing was run on unmodulated maps by mistake."
  severity: high
  recommended_action: "Confirm smoothing used the modulated maps; if unsure, re-run modulation and smoothing."
  expected_output: "mwc1*.nii (or mwp1*.nii) present, and smwc1/smwp1 derived from them."
  maps_to_status: ERROR
```

The rule *wording* lives in the YAML; the rule *detection* lives in the reasoner.
If PyYAML isn't installed, the reasoner falls back to an embedded copy of the
rules so it never hard-fails.

## How to run

From the repo root, in the `adk` environment:

```powershell
python -m my_agent.generate_vbm_qc_reportsW5
```

Or QC a single folder from Python:

```python
from my_agent.vbm_qc_reasoner import run_vbm_qc
result = run_vbm_qc("test_vbm_problem")
print(result["qc_status"])          # ERROR
print(result["markdown_report"])    # the full report
```

Through the agent, ask something like:

```
Is test_vbm_problem valid? Give me a VBM QC report.
```

The agent calls `run_vbm_qc`, reports the status, walks through each triggered
rule, and gives the tutorial explanation (what's done, what's missing, why it
matters, what to do next, and what files to expect afterward).

## The QC report

Every report has seven sections: current workflow state, detected files, missing
files, inconsistent files, QC status + warnings (with a rule-detail table),
recommended next step, and a tutorial explanation. See the three example reports
in the repo root for READY, WARNING, and ERROR cases.
