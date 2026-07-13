# VBM QC Report

**Folder:** `C:\Users\tisha\OneDrive\Pictures\Documents\Desktop\Neuro_claw_agent\test_vbm_problem`

**QC status:** `ERROR`

## 1. Current workflow state

- **State:** `INCOMPLETE_OR_ERROR`
- Files found but pipeline state is inconsistent. Later-stage files exist without expected earlier-stage files.

The files present are not consistent with a single clean pipeline run. SPM gray matter map present but c2*.nii, c3*.nii missing; tissue classes are normally written together. A DARTEL flow field (u_rc1) exists but the rigidly imported rc1*.nii, rc2*.nii it needs are missing. See the QC report for likely causes and how to fix each one.

## 2. Detected files

- **Raw T1w input:** T1_sub-01.nii

- `c1*.nii` -> c1T1_sub-01.nii
- `u_rc1*.nii` -> u_rc1T1_sub-01.nii

## 3. Missing files

- c2*.nii
- c3*.nii
- rc1*.nii
- rc2*.nii

## 4. Inconsistent files

- `c1T1_sub-01.nii`
- `u_rc1T1_sub-01.nii`

## 5. QC status and warnings

**Overall: `ERROR`**

- [HIGH] DARTEL flow field without rigid imports: The rigidly imported rc1/rc2 files were deleted after DARTEL ran, or they were never generated and the flow field belongs to a different run.
- [HIGH] Incomplete tissue segmentation: Segmentation was interrupted before writing every tissue class, the number of tissue classes was set too low, or some class files were deleted. All three tissue maps are normally written together.
- [MEDIUM] Segmentation done but deformation field missing: Segmentation was run with 'deformation fields' turned off. The y_ field is what a plain (non-DARTEL) normalization needs to warp maps to MNI.

### Rule details

| Issue | Severity | Evidence | Likely cause | Expected after fix |
|---|---|---|---|---|
| DARTEL flow field without rigid imports | high | A DARTEL flow field u_rc1*.nii exists but rc1*.nii / rc2*.nii are missing. | The rigidly imported rc1/rc2 files were deleted after DARTEL ran, or they were never generated and the flow field belongs to a different run. | rc1*.nii and rc2*.nii alongside u_rc1*.nii. |
| Incomplete tissue segmentation | high | A gray matter map (c1/p1) exists but the matching c2/p2 or c3/p3 is missing. | Segmentation was interrupted before writing every tissue class, the number of tissue classes was set too low, or some class files were deleted. All three tissue maps are normally written together. | A complete set c1/c2/c3 (or p1/p2/p3), one per tissue class. |
| Segmentation done but deformation field missing | medium | c1/c2/c3 are present but the forward deformation field y_*.nii is missing. | Segmentation was run with 'deformation fields' turned off. The y_ field is what a plain (non-DARTEL) normalization needs to warp maps to MNI. | y_*.nii next to the c1/c2/c3 tissue maps. |

## 6. Recommended next step

- Re-run DARTEL import to regenerate rc1/rc2, then confirm the flow field was built from those same imports before normalizing.
- Re-run segmentation and make sure it is configured to write gray matter, white matter, and CSF (native + DARTEL-imported if using SPM-DARTEL).
- If you plan to use DARTEL you can ignore this. Otherwise re-run segmentation with the forward deformation field enabled.

## 7. Tutorial explanation

**What has been completed:** Some VBM files exist, but the set is inconsistent or incomplete.

**What is missing:**
- c2*.nii
- c3*.nii
- rc1*.nii
- rc2*.nii

**Why the missing step matters:** A pipeline can finish a step without an error and still leave an inconsistent file set. Trusting it would push a silent problem into every downstream measurement. Right now the file set is inconsistent, so fixing that comes before any next step.

**What you should do next:** Re-run DARTEL import to regenerate rc1/rc2, then confirm the flow field was built from those same imports before normalizing.

**Files that should appear after the next step:**
- rc1*.nii and rc2*.nii alongside u_rc1*.nii.
- A complete set c1/c2/c3 (or p1/p2/p3), one per tissue class.
- y_*.nii next to the c1/c2/c3 tissue maps.
