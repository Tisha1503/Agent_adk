import os
import fnmatch

from my_agent.vbm_filename_dictionary import VBM_FILENAME_DICTIONARY

VBM_STATES = {
    "RAW_T1_READY": (
        "Raw T1w image found. No VBM outputs yet. Pipeline has not started."
    ),
    "SEGMENTATION_COMPLETED": (
        "Tissue segmentation done. Gray matter, white matter, and CSF maps are present."
    ),
    "DARTEL_INPUT_READY": (
        "DARTEL import done. Rigidly aligned tissue maps are ready for DARTEL alignment."
    ),
    "DARTEL_COMPLETED": (
        "DARTEL alignment done. Subject flow fields and study templates are present."
    ),
    "NORMALIZATION_COMPLETED": (
        "Normalization done. Warped (and possibly modulated) maps in MNI space are present."
    ),
    "SMOOTHING_COMPLETED": (
        "Smoothing done. Final VBM inputs exist but not all earlier files have been verified."
    ),
    "VBM_READY_FOR_STATISTICS": (
        "Full pipeline complete. All prerequisite files verified. Ready for second-level statistics."
    ),
    "INCOMPLETE_OR_ERROR": (
        "Files found but pipeline state is inconsistent. "
        "Later-stage files exist without expected earlier-stage files."
    ),
}

_VBM_PREFIXES = {
    "c1", "c2", "c3", "y_", "rc1", "rc2", "u_",
    "wc1", "wc2", "wp1", "wp2",
    "mwc1", "mwc2", "mwp1",
    "smwc1", "smwc2", "smwp1",
    "p0", "p1", "p2", "p3", "cat_", "Template_",
}


def _match_patterns(files, patterns):
    matched = {}
    for pattern in patterns:
        hits = [f for f in files if fnmatch.fnmatch(f, pattern)]
        if hits:
            matched[pattern] = hits
    return matched


def _is_raw_t1(filename):
    if not (filename.endswith(".nii") or filename.endswith(".nii.gz")):
        return False
    lower = filename.lower()
    for prefix in _VBM_PREFIXES:
        if lower.startswith(prefix.lower()):
            return False
    return True


def _subject_ids(files, prefix):
    """Return the set of subject identifiers among files starting with prefix.

    A subject id is whatever is left after stripping the tissue-class prefix and
    the .nii/.nii.gz extension, e.g. 'c1sub-01_T1.nii' -> 'sub-01_T1'. This lets
    us compare which subjects reached one stage versus another.
    """
    ids = set()
    for f in files:
        if f.startswith(prefix):
            stem = f[len(prefix):]
            for ext in (".nii.gz", ".nii"):
                if stem.endswith(ext):
                    stem = stem[: -len(ext)]
                    break
            ids.add(stem)
    return ids


def analyze_vbm_inconsistencies(files) -> list:
    """Look for logically inconsistent combinations of VBM output files.

    These are situations where the files present cannot all come from a single,
    clean pipeline run: a later stage exists without the earlier stage that must
    have produced its input, a tissue set is only partly written, or a group
    DARTEL run only covered some subjects. Each hit is returned as a dict with a
    stable ``rule_id`` (matched by the Week 5 QC reasoner), a human ``detail``,
    and the specific ``files`` that triggered it.

    Args:
        files: List of filenames in the subject/study folder.

    Returns:
        A list of inconsistency dicts. Empty when nothing looks wrong.
    """
    def match(pattern):
        return [f for f in files if fnmatch.fnmatch(f, pattern)]

    issues = []

    for gm, wm, csf, conv in (
        ("c1*.nii", "c2*.nii", "c3*.nii", "SPM"),
        ("p1*.nii", "p2*.nii", "p3*.nii", "CAT12"),
    ):
        if match(gm) and not (match(wm) and match(csf)):
            missing = []
            if not match(wm):
                missing.append(wm)
            if not match(csf):
                missing.append(csf)
            issues.append({
                "rule_id": "partial_segmentation",
                "detail": (
                    f"{conv} gray matter map present but {', '.join(missing)} "
                    f"missing; tissue classes are normally written together."
                ),
                "files": match(gm),
                "missing": missing,
            })

    if match("u_rc1*.nii") and not (match("rc1*.nii") and match("rc2*.nii")):
        missing = [p for p in ("rc1*.nii", "rc2*.nii") if not match(p)]
        issues.append({
            "rule_id": "flowfield_without_import",
            "detail": (
                "A DARTEL flow field (u_rc1) exists but the rigidly imported "
                f"{', '.join(missing)} it needs are missing."
            ),
            "files": match("u_rc1*.nii"),
            "missing": missing,
        })

    import_ids = _subject_ids(files, "rc1")
    flow_ids = _subject_ids(files, "u_rc1")
    if flow_ids and import_ids and import_ids != flow_ids:
        without_flow = sorted(import_ids - flow_ids)
        if without_flow:
            issues.append({
                "rule_id": "partial_dartel_subjects",
                "detail": (
                    f"{len(import_ids)} subject(s) have DARTEL imports but "
                    f"{len(without_flow)} have no flow field: "
                    f"{', '.join(without_flow)}."
                ),
                "files": match("u_rc1*.nii"),
                "missing": without_flow,
            })

    for sm, mw, conv in (
        ("smwc1*.nii", "mwc1*.nii", "SPM"),
        ("smwp1*.nii", "mwp1*.nii", "CAT12"),
    ):
        if match(sm) and not match(mw):
            issues.append({
                "rule_id": "smoothed_without_modulated",
                "detail": (
                    f"{conv} smoothed maps ({sm}) exist but the modulated "
                    f"input ({mw}) is missing."
                ),
                "files": match(sm),
                "missing": [mw],
            })

    return issues


def detect_vbm_state(folder_path: str) -> dict:
    """Scan a subject folder and classify it into a formal VBM pipeline state.

    Checks for output files from each VBM step in reverse pipeline order to
    identify the furthest completed stage. Validates logical consistency so
    that later-stage files without earlier-stage files are flagged. Works for
    both SPM-DARTEL (c1/wc1/mwc1/smwc1) and CAT12 (p1/wp1/mwp1/smwp1).

    Args:
        folder_path: Path to a subject's VBM output folder.

    Returns:
        A dict with status, detected_state, state_description, found_files,
        missing_for_next_step, input_t1_found, input_t1_files, and summary.
    """
    if not os.path.isdir(folder_path):
        return {
            "status": "error",
            "message": f"Folder not found: {folder_path}",
        }

    files = os.listdir(folder_path)

    t1_files = [f for f in files if _is_raw_t1(f)]
    input_t1_found = len(t1_files) > 0

    seg_spm = _match_patterns(files, {"c1*.nii", "c2*.nii", "c3*.nii"})
    seg_cat12 = _match_patterns(files, {"p1*.nii", "p2*.nii", "p3*.nii"})
    dartel_import = _match_patterns(files, {"rc1*.nii", "rc2*.nii"})
    dartel_align = _match_patterns(files, {"u_rc1*.nii", "Template_*.nii"})
    norm = _match_patterns(files, {"wc1*.nii", "wp1*.nii", "mwc1*.nii", "mwp1*.nii"})
    smooth = _match_patterns(files, {"smwc1*.nii", "smwp1*.nii"})

    has_seg = bool(seg_spm) or bool(seg_cat12)
    has_dartel_import = bool(dartel_import)
    has_dartel_align = bool(dartel_align)
    has_norm = bool(norm)
    has_smooth = bool(smooth)

    found_files = {}
    found_files.update(seg_spm)
    found_files.update(seg_cat12)
    found_files.update(dartel_import)
    found_files.update(dartel_align)
    found_files.update(norm)
    found_files.update(smooth)

    inconsistencies = analyze_vbm_inconsistencies(files)
    inconsistent_files = sorted(
        {f for issue in inconsistencies for f in issue.get("files", [])}
    )
    inconsistency_ids = {issue["rule_id"] for issue in inconsistencies}

    later_without_seg = (
        (has_smooth and not has_seg)
        or (has_norm and not has_seg)
        or (has_dartel_align and not has_seg)
    )
    is_inconsistent = later_without_seg or bool(inconsistencies)

    if is_inconsistent:
        state = "INCOMPLETE_OR_ERROR"
        missing = []
        if inconsistencies:
            summary = (
                "The files present are not consistent with a single clean pipeline run. "
                + " ".join(issue["detail"] for issue in inconsistencies)
                + " See the QC report for likely causes and how to fix each one."
            )
        else:
            summary = (
                "Later-stage VBM files are present but earlier segmentation files are missing. "
                "This usually means files were deleted or moved after preprocessing ran. "
                "Check that c1/c2/c3 (SPM) or p1/p2/p3 (CAT12) tissue maps are in this folder."
            )

    elif has_smooth:
        all_prereqs = has_seg and has_norm
        if all_prereqs:
            state = "VBM_READY_FOR_STATISTICS"
            missing = []
            summary = (
                "The full VBM pipeline is complete. Smoothed modulated warped gray matter "
                "maps are present along with all prerequisite files. This folder is ready "
                "for second-level statistical analysis."
            )
        else:
            state = "SMOOTHING_COMPLETED"
            missing = []
            summary = (
                "Smoothed VBM outputs are present, but not all earlier-stage files could "
                "be verified in this folder. The final inputs for statistics exist. "
                "Consider confirming that segmentation and normalization files are also present."
            )

    elif has_norm:
        state = "NORMALIZATION_COMPLETED"
        missing = ["smwc1*.nii or smwp1*.nii (smoothed modulated warped gray matter)"]
        summary = (
            "Normalized (and/or modulated) warped maps are present in MNI space. "
            "The next step is smoothing, which applies a Gaussian blur to prepare "
            "the data for voxel-wise statistical testing."
        )

    elif has_dartel_align:
        state = "DARTEL_COMPLETED"
        missing = ["wc1*.nii or wp1*.nii (warped maps in MNI space)"]
        summary = (
            "DARTEL alignment is complete. Subject-specific flow fields and study templates "
            "are present. The next step is normalization, which uses these flow fields to "
            "warp each subject's tissue maps into MNI standard space."
        )

    elif has_dartel_import:
        state = "DARTEL_INPUT_READY"
        missing = [
            "u_rc1*.nii (DARTEL flow field)",
            "Template_0.nii through Template_6.nii (study templates)",
        ]
        summary = (
            "DARTEL import is done. Rigidly aligned tissue maps are ready. "
            "The next step is running DARTEL alignment across all subjects to build "
            "a study-specific template and compute each subject's warp."
        )

    elif has_seg:
        state = "SEGMENTATION_COMPLETED"
        missing = [
            "rc1*.nii, rc2*.nii (for SPM-DARTEL) or wc1*.nii / wp1*.nii (for CAT12 normalization)"
        ]
        summary = (
            "Tissue segmentation is complete. Gray matter, white matter, and CSF probability "
            "maps are present. The next step depends on your pipeline: for SPM-DARTEL, run "
            "DARTEL import; for CAT12, proceed directly to normalization."
        )

    elif input_t1_found:
        state = "RAW_T1_READY"
        missing = [
            "c1*.nii, c2*.nii, c3*.nii (SPM segmentation) or p1*.nii, p2*.nii, p3*.nii (CAT12 segmentation)"
        ]
        summary = (
            "A raw T1w image is present but no VBM preprocessing outputs have been found. "
            "The first step is tissue segmentation, which produces gray matter, white matter, "
            "and CSF probability maps that every downstream step depends on."
        )

    else:
        state = "INCOMPLETE_OR_ERROR"
        missing = ["T1w input image (.nii or .nii.gz)", "Any recognizable VBM output files"]
        summary = (
            "No recognizable T1w input or VBM output files were found in this folder. "
            "Make sure the folder contains the subject's data and that filenames follow "
            "SPM or CAT12 naming conventions."
        )

    return {
        "status": "success",
        "detected_state": state,
        "state_description": VBM_STATES.get(state, ""),
        "found_files": found_files,
        "input_t1_found": input_t1_found,
        "input_t1_files": t1_files,
        "missing_for_next_step": missing,
        "inconsistencies": inconsistencies,
        "inconsistent_files": inconsistent_files,
        "inconsistency_ids": sorted(inconsistency_ids),
        "folder_path": folder_path,
        "summary": summary,
    }
