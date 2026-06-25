# VBM File-Name Dictionary

A reference for SPM-based VBM output files. SPM uses a strict prefix
convention where each preprocessing step adds a letter to the front of
the filename. Reading the prefixes right-to-left reconstructs the
pipeline history.

## Prefix legend

| Prefix | Meaning              |
|--------|----------------------|
| `c1`   | Class 1 = gray matter (from segmentation) |
| `c2`   | Class 2 = white matter |
| `c3`   | Class 3 = CSF (cerebrospinal fluid) |
| `r`    | Rigidly imported for DARTEL |
| `u_`   | Subject-specific DARTEL flow field |
| `w`    | Warped (normalized to template space) |
| `m`    | Modulated (Jacobian-adjusted to preserve volume) |
| `s`    | Smoothed (Gaussian kernel applied) |

## File reference

### Segmentation outputs

| File pattern   | What it is | Stage signature |
|----------------|------------|-----------------|
| `c1*.nii`      | Gray matter tissue probability map | Segmentation complete |
| `c2*.nii`      | White matter tissue probability map | Segmentation complete |
| `c3*.nii`      | CSF tissue probability map | Segmentation complete |
| `y_*.nii`      | Forward deformation field (warp to MNI) | Segmentation complete |
| `iy_*.nii`     | Inverse deformation field | Segmentation complete |
| `m*.nii`       | Bias-corrected input image | Segmentation complete |

### DARTEL preparation

| File pattern   | What it is | Stage signature |
|----------------|------------|-----------------|
| `rc1*.nii`     | Rigidly imported gray matter (DARTEL input) | DARTEL import done |
| `rc2*.nii`     | Rigidly imported white matter (DARTEL input) | DARTEL import done |

### DARTEL alignment

| File pattern        | What it is | Stage signature |
|---------------------|------------|-----------------|
| `Template_0.nii` ... `Template_6.nii` | Iteratively-built study templates | DARTEL alignment running/done |
| `u_rc1*.nii`        | Subject-specific DARTEL flow field (the warp) | DARTEL alignment complete |

### Normalization (warping)

| File pattern   | What it is | Stage signature |
|----------------|------------|-----------------|
| `wc1*.nii`     | Warped gray matter map (in standard space) | Normalization complete |
| `wc2*.nii`     | Warped white matter map | Normalization complete |
| `wp1*.nii`     | Warped gray matter (CAT12 naming convention) | Normalization complete |

### Modulation

| File pattern   | What it is | Stage signature |
|----------------|------------|-----------------|
| `mwc1*.nii`    | Modulated warped gray matter | Modulation complete |
| `mwc2*.nii`    | Modulated warped white matter | Modulation complete |
| `mwp1*.nii`    | Modulated warped gray matter (CAT12) | Modulation complete |

### Smoothing (final input to statistics)

| File pattern   | What it is | Stage signature |
|----------------|------------|-----------------|
| `smwc1*.nii`   | Smoothed modulated warped gray matter | Smoothing complete |
| `smwc2*.nii`   | Smoothed modulated warped white matter | Smoothing complete |
| `smwp1*.nii`   | Smoothed modulated warped GM (CAT12) | Smoothing complete |

## Reading a file name

The prefixes stack. Read them right-to-left to recover the pipeline history:

`smwc1T1.nii`  →  `s` + `m` + `w` + `c1` + `T1`
                   ↑    ↑    ↑     ↑      ↑
              smoothed  |   warped  |   original
                    modulated     gray matter

That single filename tells you: this is the original T1, segmented to
gray matter, then warped to standard space, then modulated to preserve
volume, then smoothed. All four preprocessing steps complete.

## Why this matters

The prefix convention is what lets you (or an agent) look at a folder
and immediately tell which pipeline stage has been reached:

- See only `c1*.nii`, `c2*.nii`, `c3*.nii`  → segmentation done, normalization not yet
- See `wc1*.nii` but no `mwc1*.nii`           → normalization done, modulation pending
- See `mwc1*.nii` but no `smwc1*.nii`         → modulation done, smoothing pending
- See `smwc1*.nii`                            → preprocessing complete; ready for statistics

This is the foundation for Week 4's automated stage detection.

## Note on naming variants

SPM-DARTEL uses `c1` / `wc1` / `mwc1` / `smwc1`.
CAT12 (a modernized SPM-based VBM tool) uses `p1` / `wp1` / `mwp1` / `smwp1` for the same logical files.

Both conventions follow the same prefix system; only the tissue class letter differs (`c` vs `p`). Most labs use one or the other consistently, so confirm which your pipeline uses before scripting.
