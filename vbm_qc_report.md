# VBM QC Report

**Folder:** `C:\Users\tisha\OneDrive\Pictures\Documents\Desktop\Neuro_claw_agent\test_vbm_subject`

**QC status:** `WARNING`

## 1. Current workflow state

- **State:** `SEGMENTATION_COMPLETED`
- Tissue segmentation done. Gray matter, white matter, and CSF maps are present.

Tissue segmentation is complete. Gray matter, white matter, and CSF probability maps are present. The next step depends on your pipeline: for SPM-DARTEL, run DARTEL import; for CAT12, proceed directly to normalization.

## 2. Detected files

- **Raw T1w input:** T1.nii

- `c3*.nii` -> c3T1.nii
- `c2*.nii` -> c2T1.nii
- `c1*.nii` -> c1T1.nii

## 3. Missing files

- rc1*.nii, rc2*.nii (for SPM-DARTEL) or wc1*.nii / wp1*.nii (for CAT12 normalization)

## 4. Inconsistent files

- (none — the file set is internally consistent)

## 5. QC status and warnings

**Overall: `WARNING`**

- [MEDIUM] Segmentation done but deformation field missing: Segmentation was run with 'deformation fields' turned off. The y_ field is what a plain (non-DARTEL) normalization needs to warp maps to MNI.

### Rule details

| Issue | Severity | Evidence | Likely cause | Expected after fix |
|---|---|---|---|---|
| Segmentation done but deformation field missing | medium | c1/c2/c3 are present but the forward deformation field y_*.nii is missing. | Segmentation was run with 'deformation fields' turned off. The y_ field is what a plain (non-DARTEL) normalization needs to warp maps to MNI. | y_*.nii next to the c1/c2/c3 tissue maps. |

## 6. Recommended next step

- If you plan to use DARTEL you can ignore this. Otherwise re-run segmentation with the forward deformation field enabled.

## 7. Tutorial explanation

**What has been completed:** Tissue segmentation is done: gray matter, white matter, and CSF maps exist.

**What is missing:**
- rc1*.nii, rc2*.nii (for SPM-DARTEL) or wc1*.nii / wp1*.nii (for CAT12 normalization)

**Why the missing step matters:** Segmentation gives per-tissue probability maps, but they are still in each subject's native space, so subjects are not yet comparable to one another.

**What you should do next:** For SPM-DARTEL, run DARTEL import (rc1/rc2). For CAT12, proceed to normalization.

**Files that should appear after the next step:**
- rc1*.nii
- rc2*.nii
