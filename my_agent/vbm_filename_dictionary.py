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
