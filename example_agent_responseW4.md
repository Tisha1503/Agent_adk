# Example Agent Response

**User prompt:** What's the VBM status for test_vbm_subject/ and what should I do next?

---

## Agent Response

I scanned the folder `test_vbm_subject/` and here is what I found.

### Current state: SEGMENTATION_COMPLETED

Tissue segmentation has been completed for this subject. The folder contains three tissue probability maps from SPM Unified Segmentation:

- `c1T1.nii` -- gray matter probability map
- `c2T1.nii` -- white matter probability map
- `c3T1.nii` -- CSF probability map

A raw T1 input (`T1.nii`) is also present, which is good -- it means the source data is still here if any step needs to be rerun.

### What is missing

Before the next step can run, you need:

- `rc1*.nii` and `rc2*.nii` if you are using SPM-DARTEL (rigidly aligned tissue maps for DARTEL import)
- Or `wc1*.nii` / `wp1*.nii` if you are using CAT12 and going directly to normalization

### What to do next: DARTEL Import

The next step for an SPM-DARTEL pipeline is to run DARTEL import.

**Why this step matters:** Right now your tissue maps are still in this subject's native head space -- wherever their head happened to be positioned in the scanner. Before you can run DARTEL alignment across subjects, each person's tissue maps need to be rigidly shifted to a common starting position. Without this, the iterative DARTEL warp cannot converge on a stable group template, because subjects are starting from very different positions.

**Expected output files after this step:**

- `rc1T1.nii` -- rigidly aligned gray matter, ready for DARTEL
- `rc2T1.nii` -- rigidly aligned white matter, ready for DARTEL

**Draft SPM batch script (for reference only -- review before running):**

```matlab
matlabbatch{1}.spm.tools.dartel.impo.files{1} = {'test_vbm_subject/c1T1.nii,1'};
matlabbatch{1}.spm.tools.dartel.impo.files{2} = {'test_vbm_subject/c2T1.nii,1'};

spm_jobman('run', matlabbatch);
```

### QC checks before moving on

Before running DARTEL import, do a quick visual check on the segmentation outputs:

1. Open `c1T1.nii` and overlay it on the original `T1.nii`. The bright values should sit cleanly in the cortex and deep gray matter structures. If they are bleeding into white matter, skull, or CSF spaces, the segmentation needs to be rerun or the subject may need to be excluded.

2. Check `c2T1.nii` (white matter). It should fill the interior of the cortex and deep white matter tracts without leaking into the ventricles.

3. Check `c3T1.nii` (CSF). It should light up the ventricles and sulci, not random patches inside the brain.

If the tissue maps look clean, you are safe to proceed to DARTEL import.

---

*This is a dry-run plan. No processing has been executed. The MATLAB snippet above is a draft -- review and adapt it to your full study setup (all subjects' files need to be included in a real DARTEL run) before running.*
