"""
Week 5 VBM QC reasoner.

Takes the VBM state report produced by Week 4's ``detect_vbm_state`` and turns
it into QC reasoning: it applies the rules in ``vbm_qc_rules.yaml``, classifies
the subject as READY / WARNING / INCOMPLETE / ERROR, writes beginner-friendly
warnings and recommendations, and builds a tutorial-style explanation of what
happened and what to do next.

The rule *wording* lives in the YAML file; the rule *detection* lives here. If
PyYAML is not installed (or the file is missing), an embedded copy of the rules
is used so the reasoner never hard-fails.
"""

import os
import fnmatch

_RULES_PATH = os.path.join(os.path.dirname(__file__), "vbm_qc_rules.yaml")

_DEFAULT_RULES = [
    {
        "id": "no_recognizable_files",
        "issue": "No recognizable VBM files",
        "evidence": "The folder has neither a raw T1w image nor any SPM/CAT12 output file.",
        "likely_cause": "The folder is empty, points at the wrong location, or filenames do not follow SPM/CAT12 conventions.",
        "severity": "high",
        "recommended_action": "Confirm the path points at the subject's data folder and that the input T1w image is present.",
        "expected_output": "At minimum a raw T1w image, then c1/c2/c3 after segmentation.",
        "maps_to_status": "ERROR",
    },
    {
        "id": "later_without_segmentation",
        "issue": "Later-stage files without segmentation",
        "evidence": "Normalized, DARTEL, or smoothed files exist but c1/c2/c3 (or p1/p2/p3) are absent.",
        "likely_cause": "The tissue maps were deleted or moved after preprocessing ran.",
        "severity": "critical",
        "recommended_action": "Restore the c1/c2/c3 (or p1/p2/p3) tissue maps, or re-run segmentation.",
        "expected_output": "c1*.nii, c2*.nii, c3*.nii sitting alongside the later-stage files.",
        "maps_to_status": "ERROR",
    },
    {
        "id": "partial_segmentation",
        "issue": "Incomplete tissue segmentation",
        "evidence": "A gray matter map (c1/p1) exists but the matching c2/p2 or c3/p3 is missing.",
        "likely_cause": "Segmentation was interrupted or configured to write too few tissue classes.",
        "severity": "high",
        "recommended_action": "Re-run segmentation and ensure it writes gray matter, white matter, and CSF.",
        "expected_output": "A complete set c1/c2/c3 (or p1/p2/p3), one per tissue class.",
        "maps_to_status": "ERROR",
    },
    {
        "id": "missing_deformation_field",
        "issue": "Segmentation done but deformation field missing",
        "evidence": "c1/c2/c3 are present but the forward deformation field y_*.nii is missing.",
        "likely_cause": "Segmentation was run with deformation fields turned off.",
        "severity": "medium",
        "recommended_action": "Ignore if using DARTEL; otherwise re-run segmentation with the forward deformation field enabled.",
        "expected_output": "y_*.nii next to the c1/c2/c3 tissue maps.",
        "maps_to_status": "WARNING",
    },
    {
        "id": "flowfield_without_import",
        "issue": "DARTEL flow field without rigid imports",
        "evidence": "A DARTEL flow field u_rc1*.nii exists but rc1*.nii / rc2*.nii are missing.",
        "likely_cause": "The rigidly imported rc1/rc2 files were deleted after DARTEL ran.",
        "severity": "high",
        "recommended_action": "Re-run DARTEL import to regenerate rc1/rc2 before normalizing.",
        "expected_output": "rc1*.nii and rc2*.nii alongside u_rc1*.nii.",
        "maps_to_status": "ERROR",
    },
    {
        "id": "partial_dartel_subjects",
        "issue": "Only some subjects have DARTEL files",
        "evidence": "Several subjects have rc1/rc2 imports but only a subset have u_rc1 flow fields.",
        "likely_cause": "DARTEL alignment ran on a partial subject list or crashed part-way.",
        "severity": "medium",
        "recommended_action": "Re-run DARTEL alignment over the full subject list.",
        "expected_output": "One u_rc1*.nii per subject, plus Template_0..6 shared by the group.",
        "maps_to_status": "WARNING",
    },
    {
        "id": "smoothed_without_modulated",
        "issue": "Smoothed maps without modulated inputs",
        "evidence": "Smoothed maps (smwc1/smwp1) exist but the modulated maps (mwc1/mwp1) are missing.",
        "likely_cause": "Modulated inputs were deleted, or smoothing was run on unmodulated maps by mistake.",
        "severity": "high",
        "recommended_action": "Confirm smoothing used the modulated maps; if unsure, re-run modulation and smoothing.",
        "expected_output": "mwc1*.nii (or mwp1*.nii) present, and smwc1/smwp1 derived from them.",
        "maps_to_status": "ERROR",
    },
    {
        "id": "normalized_not_modulated",
        "issue": "Warped maps present but not modulated",
        "evidence": "Warped maps (wc1/wp1) exist but no modulated maps (mwc1/mwp1) were produced.",
        "likely_cause": "Normalization ran without modulation.",
        "severity": "low",
        "recommended_action": "Choose deliberately: modulated maps for volume, unmodulated for density.",
        "expected_output": "mwc1*.nii / mwp1*.nii if you intend to measure volume.",
        "maps_to_status": "WARNING",
    },
    {
        "id": "smoothing_unverified",
        "issue": "Smoothed outputs but earlier files unverified",
        "evidence": "Smoothed final inputs exist but not every earlier-stage file was found.",
        "likely_cause": "Intermediate files were cleaned up after preprocessing to save space.",
        "severity": "low",
        "recommended_action": "Confirm segmentation and normalization outputs exist somewhere for reproducibility.",
        "expected_output": "A verifiable trail of c1/c2/c3, wc1/mwc1, and smwc1 files.",
        "maps_to_status": "WARNING",
    },
    {
        "id": "pipeline_complete",
        "issue": "Pipeline complete",
        "evidence": "Smoothed modulated warped maps exist and every prerequisite file was verified.",
        "likely_cause": "The full VBM pipeline ran end to end and left a complete file trail.",
        "severity": "low",
        "recommended_action": "Proceed to second-level statistics (design matrix, covariates, TIV, correction).",
        "expected_output": "smwc1*.nii / smwp1*.nii ready as inputs to the group model.",
        "maps_to_status": "READY",
    },
]

_SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}

_STAGE_TUTORIAL = {
    "RAW_T1_READY": {
        "completed": "A raw T1w structural image is present. No preprocessing has run yet.",
        "why_it_matters": (
            "Everything downstream depends on segmentation, which splits the T1 into "
            "gray matter, white matter, and CSF. Without it there is nothing to warp or measure."
        ),
        "next_step": "Run tissue segmentation on the T1w image.",
        "expected_files": ["c1*.nii", "c2*.nii", "c3*.nii", "y_*.nii (SPM) or p1/p2/p3 (CAT12)"],
    },
    "SEGMENTATION_COMPLETED": {
        "completed": "Tissue segmentation is done: gray matter, white matter, and CSF maps exist.",
        "why_it_matters": (
            "Segmentation gives per-tissue probability maps, but they are still in each "
            "subject's native space, so subjects are not yet comparable to one another."
        ),
        "next_step": (
            "For SPM-DARTEL, run DARTEL import (rc1/rc2). For CAT12, proceed to normalization."
        ),
        "expected_files": ["rc1*.nii", "rc2*.nii"],
    },
    "DARTEL_INPUT_READY": {
        "completed": "Rigidly aligned tissue maps (rc1/rc2) are ready for DARTEL.",
        "why_it_matters": (
            "DARTEL builds a study-specific template and a per-subject warp (flow field). "
            "This is what makes anatomy line up across subjects far better than affine warping."
        ),
        "next_step": "Run DARTEL alignment across all subjects.",
        "expected_files": ["u_rc1*.nii", "Template_0.nii .. Template_6.nii"],
    },
    "DARTEL_COMPLETED": {
        "completed": "DARTEL alignment is done: flow fields and study templates exist.",
        "why_it_matters": (
            "The flow fields describe how to deform each subject into the group template, "
            "but the tissue maps have not yet been written out into standard MNI space."
        ),
        "next_step": "Run normalization to MNI, with modulation if you want volume.",
        "expected_files": ["wc1*.nii", "mwc1*.nii (modulated)"],
    },
    "NORMALIZATION_COMPLETED": {
        "completed": "Warped (and possibly modulated) maps in MNI space exist.",
        "why_it_matters": (
            "The maps are now in a common space and comparable across subjects, but they are "
            "still noisy voxel-for-voxel and violate the smoothness the statistics assume."
        ),
        "next_step": "Run Gaussian smoothing (commonly 8 mm FWHM).",
        "expected_files": ["smwc1*.nii", "smwp1*.nii"],
    },
    "SMOOTHING_COMPLETED": {
        "completed": "Smoothed final VBM inputs exist.",
        "why_it_matters": (
            "The final inputs are ready, but not every earlier-stage file was verified in this "
            "folder, so the run is harder to audit or reproduce."
        ),
        "next_step": "Confirm the earlier segmentation/normalization files exist, then run statistics.",
        "expected_files": ["smwc1*.nii / smwp1*.nii (already present)"],
    },
    "VBM_READY_FOR_STATISTICS": {
        "completed": "The full pipeline is complete and every prerequisite file was verified.",
        "why_it_matters": (
            "The smoothed modulated warped maps are valid inputs to a group model. The remaining "
            "risks are study-design ones: covariates, TIV, and multiple-comparison correction."
        ),
        "next_step": "Set up second-level statistics with age, sex, and TIV covariates.",
        "expected_files": ["SPM.mat and thresholded statistical maps"],
    },
    "INCOMPLETE_OR_ERROR": {
        "completed": "Some VBM files exist, but the set is inconsistent or incomplete.",
        "why_it_matters": (
            "A pipeline can finish a step without an error and still leave an inconsistent file "
            "set. Trusting it would push a silent problem into every downstream measurement."
        ),
        "next_step": "Resolve the inconsistencies listed below before continuing.",
        "expected_files": ["A consistent file trail from segmentation through smoothing"],
    },
}


def _load_rules() -> dict:
    """Load QC rules, preferring the YAML file and falling back to the embedded copy."""
    try:
        import yaml

        with open(_RULES_PATH, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        rules = data.get("rules") if isinstance(data, dict) else None
        if rules:
            return {r["id"]: r for r in rules}
    except Exception:
        pass
    return {r["id"]: r for r in _DEFAULT_RULES}


def _all_files_from_report(report: dict) -> list:
    """Recover the folder's file list, from disk if possible, else from the report."""
    folder = report.get("folder_path")
    if folder and os.path.isdir(folder):
        return os.listdir(folder)

    files = set(report.get("input_t1_files", []) or [])
    for hits in (report.get("found_files") or {}).values():
        files.update(hits)
    files.update(report.get("inconsistent_files", []) or [])
    return sorted(files)


def _triggered_rule_ids(report: dict, files: list) -> list:
    """Decide which QC rule ids apply to this state report. Order = report order."""
    def has(pattern):
        return any(fnmatch.fnmatch(f, pattern) for f in files)

    ids = []
    state = report.get("detected_state")
    found = report.get("found_files") or {}
    has_found = bool(found)

    ids.extend(report.get("inconsistency_ids", []) or [])

    if state == "INCOMPLETE_OR_ERROR" and not report.get("inconsistency_ids"):
        if not has_found and not report.get("input_t1_found"):
            ids.append("no_recognizable_files")
        elif has_found:
            ids.append("later_without_segmentation")

    seg_present = has("c1*.nii") or has("p1*.nii")
    if seg_present and not has("y_*.nii") and not has("rc1*.nii") and not has("wc1*.nii") \
            and not has("wp1*.nii"):
        ids.append("missing_deformation_field")

    warped = has("wc1*.nii") or has("wp1*.nii")
    modulated = has("mwc1*.nii") or has("mwp1*.nii")
    smoothed = has("smwc1*.nii") or has("smwp1*.nii")
    if warped and not modulated and not smoothed:
        ids.append("normalized_not_modulated")

    if state == "SMOOTHING_COMPLETED":
        ids.append("smoothing_unverified")

    if state == "VBM_READY_FOR_STATISTICS":
        ids.append("pipeline_complete")

    seen = set()
    ordered = []
    for rid in ids:
        if rid not in seen:
            seen.add(rid)
            ordered.append(rid)
    return ordered


def _classify(triggered_rules: list, state: str) -> str:
    """Fold the triggered rules into a single subject QC status."""
    statuses = {r.get("maps_to_status") for r in triggered_rules}
    if "ERROR" in statuses:
        return "ERROR"
    if "WARNING" in statuses:
        return "WARNING"
    if "READY" in statuses or state == "VBM_READY_FOR_STATISTICS":
        return "READY"
    return "INCOMPLETE"


def reason_about_vbm_qc(vbm_state_report: dict) -> dict:
    """Apply VBM QC rules to a Week 4 state report and reason about it.

    Reads the detected VBM state, matches it against the QC rules, classifies the
    subject as READY / WARNING / INCOMPLETE / ERROR, and produces plain-English
    warnings, recommendations, and a tutorial-style explanation.

    Args:
        vbm_state_report: The dict returned by ``detect_vbm_state(folder_path)``.

    Returns:
        A dict with qc_status, triggered_rules, warnings, recommendations, and a
        tutorial block. On a bad input report it returns a status="error" dict.
    """
    if not isinstance(vbm_state_report, dict):
        return {"status": "error", "message": "vbm_state_report must be a dict."}
    if vbm_state_report.get("status") == "error":
        return {
            "status": "error",
            "message": vbm_state_report.get("message", "State detection failed."),
            "qc_status": "ERROR",
        }

    rules = _load_rules()
    files = _all_files_from_report(vbm_state_report)
    state = vbm_state_report.get("detected_state", "INCOMPLETE_OR_ERROR")

    triggered_ids = _triggered_rule_ids(vbm_state_report, files)
    triggered_rules = [rules[rid] for rid in triggered_ids if rid in rules]
    triggered_rules.sort(key=lambda r: _SEVERITY_ORDER.get(r.get("severity"), 9))

    qc_status = _classify(triggered_rules, state)

    warnings = []
    recommendations = []
    for rule in triggered_rules:
        if rule.get("maps_to_status") == "READY":
            continue
        warnings.append(
            f"[{rule.get('severity', 'n/a').upper()}] {rule['issue']}: "
            f"{rule.get('likely_cause', '').strip()}"
        )
        recommendations.append(rule.get("recommended_action", "").strip())

    if not recommendations:
        recommendations.append(
            _STAGE_TUTORIAL.get(state, {}).get("next_step", "Review the workflow status.")
        )

    tutorial = build_tutorial(vbm_state_report, qc_status, triggered_rules)

    return {
        "status": "success",
        "qc_status": qc_status,
        "detected_state": state,
        "triggered_rules": [
            {
                "id": rid,
                "issue": rules[rid]["issue"],
                "severity": rules[rid].get("severity"),
                "evidence": rules[rid].get("evidence"),
                "likely_cause": rules[rid].get("likely_cause", "").strip(),
                "recommended_action": rules[rid].get("recommended_action", "").strip(),
                "expected_output": rules[rid].get("expected_output", "").strip(),
                "maps_to_status": rules[rid].get("maps_to_status"),
            }
            for rid in triggered_ids
            if rid in rules
        ],
        "warnings": warnings,
        "recommendations": recommendations,
        "tutorial": tutorial,
    }


def build_tutorial(report: dict, qc_status: str, triggered_rules: list) -> dict:
    """Build the beginner-friendly explanation: done / missing / why / next / expected."""
    state = report.get("detected_state", "INCOMPLETE_OR_ERROR")
    base = _STAGE_TUTORIAL.get(state, _STAGE_TUTORIAL["INCOMPLETE_OR_ERROR"])

    missing = list(report.get("missing_for_next_step", []) or [])
    for issue in report.get("inconsistencies", []) or []:
        for m in issue.get("missing", []) or []:
            if m not in missing:
                missing.append(m)
    if not missing:
        missing = ["Nothing required for the next step is missing."]

    if qc_status == "ERROR":
        why = (
            base["why_it_matters"]
            + " Right now the file set is inconsistent, so fixing that comes before any next step."
        )
        next_step = triggered_rules[0]["recommended_action"] if triggered_rules else base["next_step"]
        expected = [r.get("expected_output", "") for r in triggered_rules if r.get("expected_output")]
        expected_files = expected or base["expected_files"]
    else:
        why = base["why_it_matters"]
        next_step = base["next_step"]
        expected_files = base["expected_files"]

    return {
        "what_has_been_completed": base["completed"],
        "what_is_missing": missing,
        "why_it_matters": why,
        "what_to_do_next": next_step,
        "files_expected_after_next_step": expected_files,
    }


def _format_file_map(found_files: dict) -> str:
    if not found_files:
        return "- (none detected)"
    lines = []
    for pattern, hits in found_files.items():
        lines.append(f"- `{pattern}` -> {', '.join(hits)}")
    return "\n".join(lines)


def format_qc_report_markdown(state_report: dict, qc: dict) -> str:
    """Render a beginner-friendly VBM QC + tutorial report as Markdown."""
    folder = state_report.get("folder_path", "(unknown folder)")
    state = state_report.get("detected_state", "UNKNOWN")
    tut = qc.get("tutorial", {})

    inconsistent = state_report.get("inconsistent_files") or []
    missing = tut.get("what_is_missing", [])

    lines = []
    lines.append("# VBM QC Report")
    lines.append("")
    lines.append(f"**Folder:** `{folder}`")
    lines.append("")
    lines.append(f"**QC status:** `{qc.get('qc_status', 'UNKNOWN')}`")
    lines.append("")

    lines.append("## 1. Current workflow state")
    lines.append("")
    lines.append(f"- **State:** `{state}`")
    lines.append(f"- {state_report.get('state_description', '')}")
    lines.append("")
    lines.append(state_report.get("summary", ""))
    lines.append("")

    lines.append("## 2. Detected files")
    lines.append("")
    if state_report.get("input_t1_found"):
        lines.append(f"- **Raw T1w input:** {', '.join(state_report.get('input_t1_files', []))}")
    else:
        lines.append("- **Raw T1w input:** (none detected)")
    lines.append("")
    lines.append(_format_file_map(state_report.get("found_files") or {}))
    lines.append("")

    lines.append("## 3. Missing files")
    lines.append("")
    for m in missing:
        lines.append(f"- {m}")
    lines.append("")

    lines.append("## 4. Inconsistent files")
    lines.append("")
    if inconsistent:
        for f in inconsistent:
            lines.append(f"- `{f}`")
    else:
        lines.append("- (none — the file set is internally consistent)")
    lines.append("")

    lines.append("## 5. QC status and warnings")
    lines.append("")
    lines.append(f"**Overall: `{qc.get('qc_status', 'UNKNOWN')}`**")
    lines.append("")
    warnings = qc.get("warnings", [])
    if warnings:
        for w in warnings:
            lines.append(f"- {w}")
    else:
        lines.append("- No QC warnings. The file set looks clean for this stage.")
    lines.append("")

    if qc.get("triggered_rules"):
        lines.append("### Rule details")
        lines.append("")
        lines.append("| Issue | Severity | Evidence | Likely cause | Expected after fix |")
        lines.append("|---|---|---|---|---|")
        for r in qc["triggered_rules"]:
            lines.append(
                f"| {r['issue']} | {r.get('severity', '')} | {r.get('evidence', '')} "
                f"| {r.get('likely_cause', '')} | {r.get('expected_output', '')} |"
            )
        lines.append("")

    lines.append("## 6. Recommended next step")
    lines.append("")
    for rec in qc.get("recommendations", []):
        if rec:
            lines.append(f"- {rec}")
    lines.append("")

    lines.append("## 7. Tutorial explanation")
    lines.append("")
    lines.append(f"**What has been completed:** {tut.get('what_has_been_completed', '')}")
    lines.append("")
    lines.append("**What is missing:**")
    for m in tut.get("what_is_missing", []):
        lines.append(f"- {m}")
    lines.append("")
    lines.append(f"**Why the missing step matters:** {tut.get('why_it_matters', '')}")
    lines.append("")
    lines.append(f"**What you should do next:** {tut.get('what_to_do_next', '')}")
    lines.append("")
    lines.append("**Files that should appear after the next step:**")
    for f in tut.get("files_expected_after_next_step", []):
        lines.append(f"- {f}")
    lines.append("")

    return "\n".join(lines)


def run_vbm_qc(folder_path: str) -> dict:
    """Detect the VBM state of a folder and run the full QC reasoning on it.

    This is the one-call Week 5 entry point: it runs Week 4's ``detect_vbm_state``,
    applies the QC rules, classifies the subject, and also returns a ready-to-read
    Markdown report.

    Args:
        folder_path: Path to a subject's (or study's) VBM output folder.

    Returns:
        A dict with the raw state_report, the qc reasoning, and a markdown_report
        string. Returns a status="error" dict if the folder cannot be read.
    """
    from my_agent.vbm_state_detectorW4 import detect_vbm_state

    state_report = detect_vbm_state(folder_path)
    if state_report.get("status") == "error":
        return {
            "status": "error",
            "message": state_report.get("message", "Could not read folder."),
        }

    qc = reason_about_vbm_qc(state_report)
    markdown = format_qc_report_markdown(state_report, qc)

    return {
        "status": "success",
        "folder_path": folder_path,
        "qc_status": qc.get("qc_status"),
        "state_report": state_report,
        "qc": qc,
        "markdown_report": markdown,
    }


if __name__ == "__main__":
    import sys

    target = sys.argv[1] if len(sys.argv) > 1 else "test_vbm_subject"
    result = run_vbm_qc(target)
    if result.get("status") == "error":
        print("ERROR:", result.get("message"))
    else:
        print(result["markdown_report"])
