# VBM Workflow Document

A practical reference for the SPM-based VBM preprocessing pipeline. For each step, I cover what it does, the files it expects and produces, the ways it can quietly fail, and what to actually look at before moving on.

## Why this document exists

Every VBM step is solving one of two questions: what tissue is at this voxel (segmentation), or where does this voxel sit in standard anatomical space (normalization). A couple of follow-up steps then make the data usable for statistics.

The reason a document like this matters is that a pipeline finishing without errors isn't the same as a pipeline that worked. Each step can fail silently. The output files exist, the script returned successfully, and the numbers are anatomically nonsense. The point of writing this out is to make those silent failures visible, so we can catch them before they corrupt every analysis downstream.

The whole pipeline in five words: **segment, normalize, modulate, smooth, test.**

---

## Step 0: T1w Input Preparation and Orientation Checking

### What it does

Before any preprocessing can run, the T1-weighted image needs to be in a state that SPM can handle correctly. This step covers two things: confirming the file is a valid T1w structural image, and checking that its orientation is consistent with what the pipeline expects.

Orientation matters because SPM's segmentation and normalization are built around templates in a specific orientation (typically RAS — Right, Anterior, Superior). If the image header reports a different orientation, or if the header and the actual voxel data disagree, every downstream step can produce spatially flipped or misregistered results. These errors are hard to catch later and corrupt all subsequent analysis.

### Expected input

The raw T1-weighted image from the scanner. Usual formats: `.nii`, `.nii.gz`, or a DICOM folder. Typical filenames: `T1.nii`, `sub-01_T1w.nii`, or `sub-01_T1w.nii.gz`.

### What to confirm

| Check | What to look for |
|---|---|
| File format | NIfTI (`.nii` / `.nii.gz`) or DICOM — not a JPEG or PNG |
| Image dimensions | Should be 3D (a single volume), not 4D |
| Voxel size | Ideally close to 1mm isotropic (e.g. 1×1×1 mm) |
| Orientation code | Header should report a standard orientation (RAS, LAS, etc.) |
| Header–data agreement | The orientation in the header should match the visible anatomy |
| No NaN / empty data | Voxel values should be non-zero and finite across the brain |

### Where this step can fail

- DICOM-to-NIfTI conversion tools sometimes mis-set the orientation matrix. The image looks fine visually but the header is wrong, and SPM misaligns it to the template.
- 4D files (time series mistakenly saved as a structural) crash or silently use only the first volume.
- Voxel sizes far from 1mm isotropic (e.g. 1×1×5 mm) can still run but will produce lower-quality segmentations.
- Left–right flips are the single most dangerous silent failure at this stage. The image processes normally and produces no errors, but every result is anatomically mirrored.

### What to check visually

- Open the image in a viewer (FSLeyes, MRIcron, or SPM's Check Reg). Confirm you can see a brain, not noise or an empty volume.
- Check the orientation labels on the viewer axes. Anterior should be in front, left should be on the left (or right, depending on radiological vs neurological convention — just confirm it's consistent with your pipeline).
- Verify the image is 3D by confirming there is no time or volume dimension.
- Run your pipeline's header check tool (e.g. `nib.load(path).header` in Python, or `fslinfo`) and confirm the voxel dimensions match expectations.

---

## Step 1: Tissue Segmentation

### What it does

Takes the raw T1 image and labels every voxel as one of three tissue types: gray matter, white matter, or cerebrospinal fluid. The output isn't a single labeled image. It's three separate probability maps, one per tissue, where each voxel holds a value between 0 and 1.

So if `c1T1.nii` has a value of 0.92 at some voxel, that's saying "this voxel has a 92% probability of being gray matter." The corresponding values in `c2T1.nii` (white matter) and `c3T1.nii` (CSF) will be smaller, and across all three tissues they roughly add up to 1.

SPM does this with a "unified segmentation" algorithm, which also corrects bias field (slow intensity drift across the image from imperfect scanner coils) and computes an initial alignment to a template, all in one operation.

### Expected input

A T1-weighted structural MRI file in NIfTI format. Typical filename: `T1.nii` or `sub-01_T1w.nii.gz`. Should be a single 3D volume, ideally 1mm isotropic, in a standard orientation like RAS.

### Expected outputs

| File | What it is |
|---|---|
| `c1T1.nii` | Gray matter probability map (0 to 1 at each voxel) |
| `c2T1.nii` | White matter probability map |
| `c3T1.nii` | CSF probability map |
| `y_T1.nii` | Forward deformation field (the warp to MNI space) |
| `iy_T1.nii` | Inverse deformation field (warp back from MNI) |
| `mT1.nii` | Bias-corrected version of the input |

### Where this step can fail

- Poor input contrast from motion artifacts, low SNR, or unusual scanner settings produces noisy tissue maps.
- Unusual anatomy (large lesions, severe atrophy, pediatric or very elderly brains) confuses the segmentation because it deviates from what the template expects.
- A strong bias field that wasn't corrected well can overwhelm the segmentation and misclassify whole regions.
- Using adult templates on a pediatric scan distorts the result, since the templates assume an adult-shaped brain.

### What to check visually

- Overlay `c1T1.nii` on the original T1. The bright values should sit cleanly in the cortex and deep gray matter structures, not bleeding into the skull or scalp.
- Check `c2T1.nii`. White matter should fill the interior of the cortex and the deep white matter tracts. If it's leaking into CSF spaces, something's off.
- Check `c3T1.nii`. CSF should highlight the ventricles and sulci, not random patches inside the brain.
- The tissue histograms should each peak near 0 (lots of non-tissue voxels) with a smaller cluster near 1 (the high-confidence tissue voxels). Flat or noisy histograms signal problems.

---

## Step 2: Spatial Normalization (DARTEL or SHOOT)

### What it does

Warps every subject's brain so it matches a common template. After this step, voxel (100, 100, 100) corresponds to roughly the same anatomical location across subjects, which is what makes voxel-by-voxel comparison meaningful in the first place.

Modern VBM uses DARTEL or its successor SHOOT instead of warping directly to MNI. DARTEL works in two stages. First, it averages the segmentations from your actual subjects to build a study-specific template. Then it warps each subject to that template using a diffeomorphic warp (a mathematically smooth, invertible one).

The way I think about it: classic normalization is warping to a stranger. DARTEL is averaging your subjects to make a template that looks like your group, then warping each subject to that.

### Expected input

The segmentation outputs from Step 1, especially `c1*.nii` and `c2*.nii` for every subject in the study.

### Expected outputs

| File | What it is |
|---|---|
| `rc1T1.nii` | Imported, rigidly-aligned gray matter (DARTEL prep step) |
| `rc2T1.nii` | Imported, rigidly-aligned white matter |
| `Template_0.nii` ... `Template_6.nii` | DARTEL templates from each iteration of alignment |
| `u_rc1T1.nii` | The subject-specific DARTEL flow field (the warp itself) |
| `wc1T1.nii` | Warped gray matter in standard space |
| `wc2T1.nii` | Warped white matter in standard space |

The `w` prefix means warped. So `wc1T1.nii` is the warped gray matter map, the subject's gray matter now in MNI space.

### Where this step can fail

- Large lesions or severe atrophy can't be aligned cleanly to the template, so the warp distorts around those areas.
- Using adult templates on a pediatric or non-human-primate brain produces bad warps no matter how careful the rest of the pipeline is.
- DARTEL needs around 20+ subjects to build a stable template. Smaller studies need a different approach.
- Bad segmentation from Step 1 propagates here. If the tissue maps were wrong, the warp built on top of them will also be wrong.

### What to check visually

- Overlay the warped image on the DARTEL or MNI template. Major landmarks (cortex outline, ventricles, brain stem) should line up.
- Look at all the warped subjects together. They should look broadly similar, since they all match the template shape now. Any outlier stands out fast.
- Check the deformation field magnitude. Extreme warp values in small spots usually mean the warp couldn't handle that region.
- Pay extra attention to the cerebellum, ventricles, and ventral brain regions. These tend to be the common alignment trouble spots.

---

## Step 3: Modulation

### What it does

Adjusts the warped gray matter values to preserve volume information. This is the trickiest step to wrap your head around, so it's worth slowing down on.

Here's the issue. The warp from Step 2 stretched some regions and squeezed others to make each subject match the template. Stretching spreads the same amount of gray matter across more voxels, which makes density per voxel drop even though no tissue was actually lost. Squeezing does the opposite.

Modulation undoes that distortion by multiplying each voxel by the Jacobian determinant of the warp. That's a single number per voxel that says "how much was this location stretched or squeezed?" If a region was stretched by a factor of 2, multiplying by 2 restores the original total. The net effect is that the actual amount of gray matter is preserved.

This is what distinguishes measuring volume vs density:

- Modulated outputs measure **gray matter volume** (the absolute amount).
- Unmodulated outputs measure **gray matter density** (concentration, ignoring the warp's rearrangement).

Most VBM studies want volume, so modulation is on by default. But this is a real research choice. The biological question your study is asking should drive which one you want.

### Expected input

The warped gray matter map from Step 2 (`wc1T1.nii`) and the Jacobian determinant of the warp, which SPM computes from the deformation field.

### Expected outputs

| File | What it is |
|---|---|
| `mwc1T1.nii` | Modulated, warped gray matter (the volume measure) |
| `mwc2T1.nii` | Modulated, warped white matter |

The `m` prefix means modulated.

### Where this step can fail

- Modulation amplifies any error in the warp. If the warp had extreme Jacobians somewhere (severe stretch or squeeze), the modulated values in that region get extreme too, and they can dominate the statistics later.
- Running modulation when you wanted density (or skipping it when you wanted volume) gives you a result that measures the wrong biological quantity. This isn't a crash, just a quiet design mistake.
- It's hard to detect modulation errors just by looking. The output looks similar to the unmodulated version. The errors usually only show up when you check the Jacobian map directly or notice statistical outliers later.

### What to check visually

- Check the Jacobian determinant map if your pipeline saves it. It should be smooth and mostly close to 1, with no extreme spikes.
- Compare `wc1T1.nii` (unmodulated) and `mwc1T1.nii` (modulated) side by side. The modulated version will be brighter where the brain was stretched and dimmer where it was squeezed. Big visible differences in localized spots are worth a second look.
- Confirm which version (modulated or unmodulated) you actually want before moving on. Easy to mix up.

---

## Step 4: Spatial Smoothing

### What it does

Applies a Gaussian blur to each voxel, so each voxel becomes a weighted average of its neighbors. The "kernel size" controls how much blurring, usually given as FWHM (Full Width at Half Maximum) in millimeters. Common choices are 6mm or 8mm FWHM.

Smoothing exists for two reasons. First, even after DARTEL, the warp isn't perfect, and voxels may be off by a millimeter or two across subjects. Smoothing makes comparisons robust to that small residual misalignment. Second, the statistical tests used downstream (parametric tests, Gaussian Random Field theory for multiple-comparison correction) assume smooth, approximately Gaussian data. Smoothing helps that assumption hold.

The trade-off is real:

- A bigger kernel (10 to 12mm) is more robust and has better power for widespread effects, but it blurs out small focal effects.
- A smaller kernel (4 to 6mm) keeps spatial detail and can catch focal effects, but it's less robust to alignment errors and has less statistical power overall.

The rule of thumb is to match the kernel to the expected size of your effect. If you're studying widespread aging changes, 8 to 12mm is fine. If you're hunting for small focal differences, 4 to 6mm.

### Expected input

The modulated warped gray matter maps from Step 3 (`mwc1T1.nii` for all subjects).

### Expected outputs

| File | What it is |
|---|---|
| `smwc1T1.nii` | Smoothed, modulated, warped gray matter (the actual input to VBM statistics) |
| `smwc2T1.nii` | Smoothed, modulated, warped white matter |

The `s` prefix means smoothed. The full prefix stack now reads `smwc1`, which is the entire pipeline encoded in five letters: smoothed, modulated, warped, gray matter class 1.

### Where this step can fail

- Choosing the wrong kernel size for your hypothesis. Too big blurs out the effect, too small means you don't have the statistical power to find it.
- Smoothing too aggressively in small structures. Subcortical regions like the hippocampus and amygdala are small, so an 8mm kernel can wash out their signal entirely.
- Smoothing isn't really a "failure mode" the way segmentation can fail. It's a methodological choice with consequences you should be aware of going in.

### What to check visually

- Compare `mwc1T1.nii` and `smwc1T1.nii` side by side. The smoothed version should look like a blurred version of the modulated one. Same general structure, less detail.
- Confirm the kernel size matches what you wrote in your methods. Inconsistency between what was run and what's documented is a surprisingly common mistake.
- Look for over-smoothing. If you can't make out individual gyri anymore, your kernel is bigger than the questions you're asking can support.

---

## Step 5: Statistical Analysis

### What it does

Now every subject has a smoothed, modulated, warped gray matter map in standard space. Stack them and run a statistical test at every voxel comparing your groups, or correlating with a variable like age, or whatever the actual hypothesis is.

The standard framework is the General Linear Model (GLM). At every voxel, you fit: `gray matter value ~ group + age + sex + total intracranial volume + ...`. The covariates after `group` control for confounds. Without them, what looks like a group difference might actually just be an age difference in disguise.

The output is a 3D statistical map (a t-map or F-map) that you threshold to find voxels showing significant effects.

The multiple-comparisons problem is the big thing to know about. A typical VBM analysis tests around 11 million voxels. At a standard p-threshold of 0.05, you'd expect around 550,000 false positives by chance alone. Without correction, the results are meaningless. Two common correction approaches:

- **FWE (Family-Wise Error correction).** Very strict. Controls the chance of any false positive across the brain. Standard for confirmatory studies.
- **FDR (False Discovery Rate).** Less strict. Controls the proportion of false positives among significant voxels. Sometimes used for exploratory work.

### Expected input

All subjects' `smwc1T1.nii` files stacked together, a design matrix encoding group and covariates and contrasts, and each subject's total intracranial volume (TIV), which is usually included as a covariate to control for overall head size.

### Expected outputs

| File | What it is |
|---|---|
| `SPM.mat` | The full SPM analysis object: design matrix, contrasts, results |
| `beta_*.nii` | One file per regressor in the GLM, showing estimated effect size at each voxel |
| `spmT_*.nii` | t-statistic maps for each contrast |
| `spmF_*.nii` | F-statistic maps for each contrast |
| Thresholded result maps | The voxels that survive multiple-comparison correction |

### Where this step can fail

- Missing covariates. Forgetting to include age, sex, or total intracranial volume can produce "group differences" that are really demographic confounds. TIV matters especially, since without it smaller brains will look like they have less of everything.
- Wrong multiple-comparison correction. Reporting uncorrected p-values is one of the most common mistakes in VBM papers and largely indefensible.
- Underpowered design. Fewer than 20 to 30 subjects per group rarely produces stable, replicable results.
- Wrong contrast definition. Setting up the design matrix incorrectly (wrong sign, missing interaction terms) gives results that look real but don't actually test what you intended.

### What to check visually

- Look at the design matrix before running the analysis. It should visualize sensibly: groups, covariates, contrasts.
- Check the residuals after the GLM is fit. Residual variance should be roughly uniform across the brain. Big patches of high or low variance signal problems.
- Overlay significant clusters on a standard anatomical template. The clusters should fall in plausible anatomical locations, not scattered noise or ventricle edges.
- When reporting results, give effect sizes and cluster locations using an atlas (AAL, Harvard-Oxford), not just MNI coordinates. Coordinates by themselves aren't interpretable.

---

## The file-prefix mental model

If you take only one practical thing from this document, take this. SPM uses a strict filename-prefix convention, and each step adds a letter to the front of the filename. The full stack reads like a sentence describing what's been done to the file.

Starting from `T1.nii`:

| File | What the prefix means | Stage |
|---|---|---|
| `T1.nii` | (no prefix) | Raw input |
| `c1T1.nii` | `c1` = class 1 = gray matter | After segmentation |
| `rc1T1.nii` | `r` = rigidly imported for DARTEL | DARTEL prep |
| `wc1T1.nii` | `w` = warped | After normalization |
| `mwc1T1.nii` | `m` = modulated | After modulation |
| `smwc1T1.nii` | `s` = smoothed | After smoothing (input to statistics) |

Read the stack `s-m-w-c1` right-to-left and you get the whole story: smoothed, modulated, warped, gray matter.

If you (or a Week 4 agent) look at a folder and see `mwc1T1.nii` but no `smwc1T1.nii`, you know: segmentation, normalization, and modulation have run, but smoothing hasn't. That single convention is what makes automated stage detection possible.

---

## How to use this document

When working on a VBM pipeline:

1. Before running anything, confirm the input file matches Step 1's expected input.
2. After each step, check that the expected output files exist, and run through the visual QC checklist before moving on.
3. If something looks off, consult the failure points for that step before assuming something downstream is broken.
4. At the end, confirm the file prefix on the final output matches the steps you intended to run. For the standard pipeline, that's `smwc1`.

The principle running through all of this: a command finishing without an error message is not the same as the step having worked.

---

## A note on CAT12

Most modern labs use CAT12 instead of plain SPM-DARTEL. CAT12 is a more sophisticated SPM-based VBM toolbox built on the same conceptual steps. The file names shift slightly. You'll see `p0T1.nii` (final segmented label map) and the tissue prefix is `p1` instead of `c1`, so the equivalent of `smwc1T1.nii` becomes `smwp1T1.nii`. The conceptual pipeline is identical. If the lab uses CAT12, swap `c1` for `p1` in your mental model and everything else carries over.