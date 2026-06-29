"""
VBM file-name dictionary.

Maps SPM (and CAT12) output file patterns to their meanings and to the
pipeline stage they signal. This is the lookup table that an agent uses
to detect which VBM preprocessing step has been reached in a folder.
"""

VBM_FILENAME_DICTIONARY = {
    "c1*.nii": {
        "tissue": "gray matter",
        "description": "Gray matter tissue probability map (0-1 per voxel).",
        "stage": "segmentation",
        "produced_by": "SPM Unified Segmentation",
    },
    "c2*.nii": {
        "tissue": "white matter",
        "description": "White matter tissue probability map.",
        "stage": "segmentation",
        "produced_by": "SPM Unified Segmentation",
    },
    "c3*.nii": {
        "tissue": "CSF",
        "description": "Cerebrospinal fluid tissue probability map.",
        "stage": "segmentation",
        "produced_by": "SPM Unified Segmentation",
    },
    "y_*.nii": {
        "tissue": None,
        "description": "Forward deformation field (voxel -> MNI warp).",
        "stage": "segmentation",
        "produced_by": "SPM Unified Segmentation",
    },

    "rc1*.nii": {
        "tissue": "gray matter",
        "description": "Rigidly imported gray matter, ready for DARTEL.",
        "stage": "dartel_import",
        "produced_by": "DARTEL Import",
    },
    "rc2*.nii": {
        "tissue": "white matter",
        "description": "Rigidly imported white matter, ready for DARTEL.",
        "stage": "dartel_import",
        "produced_by": "DARTEL Import",
    },

    "u_rc1*.nii": {
        "tissue": None,
        "description": "Subject-specific DARTEL flow field (the warp).",
        "stage": "dartel_alignment",
        "produced_by": "DARTEL Run",
    },
    "Template_*.nii": {
        "tissue": None,
        "description": "Iteratively-built study-specific DARTEL template.",
        "stage": "dartel_alignment",
        "produced_by": "DARTEL Run",
    },

    "wc1*.nii": {
        "tissue": "gray matter",
        "description": "Warped gray matter map in MNI space.",
        "stage": "normalization",
        "produced_by": "Normalise to MNI",
    },
    "wc2*.nii": {
        "tissue": "white matter",
        "description": "Warped white matter map in MNI space.",
        "stage": "normalization",
        "produced_by": "Normalise to MNI",
    },

    "mwc1*.nii": {
        "tissue": "gray matter",
        "description": "Modulated warped gray matter (volume-preserving).",
        "stage": "modulation",
        "produced_by": "Jacobian Modulation",
    },
    "mwc2*.nii": {
        "tissue": "white matter",
        "description": "Modulated warped white matter.",
        "stage": "modulation",
        "produced_by": "Jacobian Modulation",
    },
    "mwp1*.nii": {
        "tissue": "gray matter",
        "description": "Modulated warped gray matter (CAT12 naming).",
        "stage": "modulation",
        "produced_by": "CAT12",
    },

    "smwc1*.nii": {
        "tissue": "gray matter",
        "description": "Smoothed modulated warped gray matter — final VBM input.",
        "stage": "smoothing",
        "produced_by": "Gaussian Smoothing",
    },
    "smwc2*.nii": {
        "tissue": "white matter",
        "description": "Smoothed modulated warped white matter.",
        "stage": "smoothing",
        "produced_by": "Gaussian Smoothing",
    },
    "smwp1*.nii": {
        "tissue": "gray matter",
        "description": "Smoothed modulated warped GM (CAT12 naming).",
        "stage": "smoothing",
        "produced_by": "CAT12",
    },

    "p0*.nii": {
        "tissue": "all tissues",
        "description": "CAT12 label map — one image where 1=CSF, 2=gray matter, 3=white matter.",
        "stage": "segmentation",
        "produced_by": "CAT12",
    },
    "p1*.nii": {
        "tissue": "gray matter",
        "description": "CAT12 gray matter probability map (equivalent to SPM c1).",
        "stage": "segmentation",
        "produced_by": "CAT12",
    },
    "p2*.nii": {
        "tissue": "white matter",
        "description": "CAT12 white matter probability map (equivalent to SPM c2).",
        "stage": "segmentation",
        "produced_by": "CAT12",
    },
    "p3*.nii": {
        "tissue": "CSF",
        "description": "CAT12 CSF probability map (equivalent to SPM c3).",
        "stage": "segmentation",
        "produced_by": "CAT12",
    },

    "wp1*.nii": {
        "tissue": "gray matter",
        "description": "CAT12 warped gray matter in MNI space (equivalent to SPM wc1).",
        "stage": "normalization",
        "produced_by": "CAT12",
    },
    "wp2*.nii": {
        "tissue": "white matter",
        "description": "CAT12 warped white matter in MNI space (equivalent to SPM wc2).",
        "stage": "normalization",
        "produced_by": "CAT12",
    },

    "cat_*.xml": {
        "tissue": None,
        "description": "CAT12 per-subject quality report. Contains image quality rating, noise estimate, and weighted overall score.",
        "stage": "segmentation",
        "produced_by": "CAT12",
    },
}


VBM_STAGE_ORDER = [
    "segmentation",
    "dartel_import",
    "dartel_alignment",
    "normalization",
    "modulation",
    "smoothing",
]


def explain_filename(filename: str) -> dict:
    """Look up a single VBM filename and return its meaning.

    Args:
        filename: A filename like 'mwc1sub-01_T1.nii' or 'smwp1T1.nii'.

    Returns:
        A dict with tissue, description, stage, and produced_by — or an
        error dict if no pattern matches.
    """
    import fnmatch

    for pattern, info in VBM_FILENAME_DICTIONARY.items():
        if fnmatch.fnmatch(filename, pattern):
            return {"status": "success", "matched_pattern": pattern, **info}

    return {
        "status": "error",
        "message": f"No VBM pattern matches filename '{filename}'.",
    }


def detect_vbm_stage(folder_path: str) -> dict:
    """Scan a folder and detect which VBM pipeline stage has been reached.

    Works for both SPM-DARTEL (c1/wc1/mwc1/smwc1) and CAT12 (p1/wp1/mwp1/smwp1)
    naming conventions.

    Args:
        folder_path: Path to a subject's VBM output folder.

    Returns:
        A dict with the detected stage, the files found, and the next step.
    """
    import os
    import fnmatch

    if not os.path.isdir(folder_path):
        return {"status": "error", "message": f"Folder not found: {folder_path}"}

    files = os.listdir(folder_path)

    found = {}
    for pattern, info in VBM_FILENAME_DICTIONARY.items():
        matches = [f for f in files if fnmatch.fnmatch(f, pattern)]
        if matches:
            found[pattern] = {**info, "matched_files": matches}

    if not found:
        return {
            "status": "success",
            "detected_stage": "none",
            "message": "No recognised VBM output files found. Pipeline may not have started.",
            "next_step": "Run segmentation first.",
        }

    completed_stages = {info["stage"] for info in found.values()}
    furthest = "none"
    for stage in VBM_STAGE_ORDER:
        if stage in completed_stages:
            furthest = stage

    next_step_map = {
        "segmentation": "Run DARTEL import (rc1, rc2 files).",
        "dartel_import": "Run DARTEL alignment to build templates and flow fields.",
        "dartel_alignment": "Run normalization to produce warped maps (wc1 / wp1).",
        "normalization": "Run modulation to produce volume-preserving maps (mwc1 / mwp1).",
        "modulation": "Run smoothing to produce final input (smwc1 / smwp1).",
        "smoothing": "Preprocessing complete. Ready for statistical analysis.",
    }

    return {
        "status": "success",
        "folder": folder_path,
        "detected_stage": furthest,
        "completed_stages": sorted(completed_stages),
        "found_patterns": list(found.keys()),
        "next_step": next_step_map.get(furthest, "Unknown stage."),
        "is_complete": furthest == "smoothing",
    }


if __name__ == "__main__":
    import json
    import pathlib

    stages = {}
    for pattern, info in VBM_FILENAME_DICTIONARY.items():
        stage = info["stage"]
        stages.setdefault(stage, []).append(pattern)

    output = {
        "pipeline": "SPM VBM with DARTEL and CAT12",
        "stages": [
            {
                "stage": stage,
                "expected_patterns": stages.get(stage, []),
            }
            for stage in VBM_STAGE_ORDER
        ],
        "minimum_required_for_statistics": ["smwp1*.nii"],
        "stage_order": VBM_STAGE_ORDER,
    }

    out_path = pathlib.Path(__file__).parent / "vbm_expected_outputs.json"
    out_path.write_text(json.dumps(output, indent=2))
    print(f"Written to {out_path}")
