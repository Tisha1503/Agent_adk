# VBM QC Report

**Folder:** `C:\Users\tisha\OneDrive\Pictures\Documents\Desktop\Neuro_claw_agent\test_vbm_complete`

**QC status:** `READY`

## 1. Current workflow state

- **State:** `VBM_READY_FOR_STATISTICS`
- Full pipeline complete. All prerequisite files verified. Ready for second-level statistics.

The full VBM pipeline is complete. Smoothed modulated warped gray matter maps are present along with all prerequisite files. This folder is ready for second-level statistical analysis.

## 2. Detected files

- **Raw T1w input:** T1_sub-01.nii

- `c3*.nii` -> c3T1_sub-01.nii
- `c2*.nii` -> c2T1_sub-01.nii
- `c1*.nii` -> c1T1_sub-01.nii
- `rc1*.nii` -> rc1T1_sub-01.nii
- `rc2*.nii` -> rc2T1_sub-01.nii
- `u_rc1*.nii` -> u_rc1T1_sub-01.nii
- `Template_*.nii` -> Template_0.nii, Template_1.nii, Template_2.nii, Template_3.nii, Template_4.nii, Template_5.nii, Template_6.nii
- `wc1*.nii` -> wc1T1_sub-01.nii
- `mwc1*.nii` -> mwc1T1_sub-01.nii
- `smwc1*.nii` -> smwc1T1_sub-01.nii

## 3. Missing files

- Nothing required for the next step is missing.

## 4. Inconsistent files

- (none — the file set is internally consistent)

## 5. QC status and warnings

**Overall: `READY`**

- No QC warnings. The file set looks clean for this stage.

### Rule details

| Issue | Severity | Evidence | Likely cause | Expected after fix |
|---|---|---|---|---|
| Pipeline complete | low | Smoothed modulated warped maps exist and every prerequisite file was verified. | The full VBM pipeline ran end to end and left a complete file trail. | smwc1*.nii / smwp1*.nii ready as inputs to the group model. |

## 6. Recommended next step

- Set up second-level statistics with age, sex, and TIV covariates.

## 7. Tutorial explanation

**What has been completed:** The full pipeline is complete and every prerequisite file was verified.

**What is missing:**
- Nothing required for the next step is missing.

**Why the missing step matters:** The smoothed modulated warped maps are valid inputs to a group model. The remaining risks are study-design ones: covariates, TIV, and multiple-comparison correction.

**What you should do next:** Set up second-level statistics with age, sex, and TIV covariates.

**Files that should appear after the next step:**
- SPM.mat and thresholded statistical maps
