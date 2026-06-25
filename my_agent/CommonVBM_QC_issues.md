# Common VBM QC Issues

A short reference for the things that go wrong most often in VBM pipelines, grouped by stage. This isn't an exhaustive list of every possible failure mode, just the ones that come up often enough to actually watch for.

## Input quality issues (caught before preprocessing)

These are the things our Week 2 inspection tool already screens for. Catching them at the front door saves hours of wasted compute, since a pipeline running on bad input data was never going to give a useful answer.

- **Wrong modality.** Someone hands in fMRI (4D shape) thinking it's a structural scan. Easy to catch with an `ndim == 3` check.
- **Anisotropic voxels.** Thick slices like 1×1×3mm degrade every downstream measurement of cortical thickness or volume.
- **Cropped field of view.** The scan doesn't contain the whole brain. FreeSurfer and SPM both struggle when the cortex is clipped.
- **Wrong orientation.** A silent L/R flip mirrors the brain. Nothing crashes, but every measurement is on the wrong hemisphere.
- **Empty or corrupted data.** NaN values, all-zero images, or impossible zero-voxel ratios.

## Segmentation issues

- **Tissue maps look noisy or speckled.** Usually a sign of poor input contrast, motion artifacts, or low SNR. The gray matter map should look like a coherent cortical ribbon, not scattered patches.
- **Gray matter probability bleeding into the skull or scalp.** Means the segmentation is mistakenly labeling non-brain tissue. Often happens when skull stripping in the input was incomplete.
- **White matter showing up in CSF spaces.** Indicates poor tissue contrast or a strong, uncorrected bias field.
- **Misclassified pediatric or elderly brains.** Default adult templates don't fit younger or older anatomy well, and segmentation gets noticeably worse on those scans.
- **Flat tissue histograms.** Each tissue map should peak near 0 (background) with a smaller cluster near 1 (high-confidence tissue voxels). A flat or noisy histogram usually means the algorithm couldn't separate the tissues confidently.

## Normalization / DARTEL issues

- **Warped image doesn't line up with the template.** Overlay them and check the cortex outline, ventricles, and brain stem. If anatomical landmarks are off, normalization failed.
- **Distorted warps around lesions or large ventricles.** The warp can't squeeze a damaged or atrophied brain to match a healthy template, so the output looks fine elsewhere but is wrong near the abnormality.
- **One subject looks very different from the others.** When you stack all warped subjects together, outliers stand out fast. Usually means the warp failed for that individual, often because their anatomy is far from the group template.
- **Unstable DARTEL templates.** If the study has fewer than 20 subjects, or the population is very heterogeneous, the iteratively-built template may not converge to anything anatomically meaningful.
- **Cerebellum or ventral brain misalignment.** These are common alignment trouble spots even when the rest of the brain looks fine. Worth a specific look.

## Modulation issues

Modulation rarely fails outright, but it does two things that need watching.

- **Amplifies warp errors.** Extreme Jacobian values from a bad warp get multiplied through to the modulated map, where they can dominate the statistics later.
- **Wrong choice between modulated and unmodulated.** Running modulation when you wanted density, or skipping it when you wanted volume, gives a result that measures the wrong biological quantity. No error message, just a quietly wrong answer.
- **Hard to spot visually.** Modulated and unmodulated maps look similar at a glance. The check is usually whether the Jacobian map itself looks smooth and reasonable.

## Smoothing issues

Smoothing isn't really a "failure mode" the way segmentation is, but the choice has real consequences.

- **Kernel too big for the structure of interest.** An 8mm kernel can wash out signal in small subcortical regions like the hippocampus or amygdala.
- **Kernel too small for the statistical assumptions.** Smoothing too lightly leaves residual misalignment uncorrected and weakens the statistics downstream.
- **Methodology mismatch.** The pipeline ran with one kernel size, but the paper reports another. Surprisingly common, so always confirm the actual value used.

## Statistical analysis issues

These are study-design problems rather than pipeline failures, but they invalidate results just as completely.

- **Missing covariates.** Forgetting to include age, sex, or total intracranial volume (TIV). Without TIV especially, smaller brains look like they "have less" of everything, masquerading as a group effect.
- **Uncorrected p-values.** Reporting raw p < 0.05 across ~11 million voxels guarantees hundreds of thousands of false positives. Multiple-comparison correction (FWE or FDR) isn't optional.
- **Underpowered sample.** Fewer than 20 to 30 subjects per group rarely gives stable, replicable findings.
- **Wrong contrast definition.** Sign errors in the design matrix or missing interaction terms produce results that look interpretable but answer the wrong question.
- **Significant clusters in implausible locations.** Clusters falling on ventricle edges, outside the brain mask, or in scattered noise patterns usually point to a preprocessing problem, not a real effect.

## Where these issues fit in our project

The Week 2 input inspection tool already handles the first set (input quality). The QC reasoning planned for Week 5 will cover segmentation and normalization issues, since those produce visible file outputs the agent can check programmatically. The modulation, smoothing, and statistical issues are mostly methodological choices the user has to make consciously. The agent's job there isn't to silently pick a default, it's to surface the choice and explain the trade-offs so the user makes it deliberately.

## The unifying principle

A pipeline can finish at any stage without throwing an error and still be wrong. Every issue in this list exists because some step "succeeded" while producing anatomically nonsense output. That's the whole reason for building a QC-aware agent: catch those silent failures before they propagate into every measurement downstream.