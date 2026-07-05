def generate_spm_batch_template(state: str, input_files: dict) -> dict:
    """Generate a draft SPM batch plan for the next VBM preprocessing step.

    Takes the current pipeline state (as returned by detect_vbm_state) and a
    dict of input file paths, and returns a matlab_snippet and a json_plan
    for the next step. Covers both SPM-DARTEL and CAT12 pipelines. Always
    returns a dry-run plan and never executes any processing.

    Args:
        state: One of the VBM pipeline state strings returned by detect_vbm_state
               (e.g. 'RAW_T1_READY', 'SEGMENTATION_COMPLETED').
        input_files: Dict mapping file roles to paths, e.g.
                     {'t1': '/path/to/T1.nii'} or
                     {'c1': '/path/to/c1T1.nii', 'c2': '/path/to/c2T1.nii'}.

    Returns:
        A dict with status, step_name, spm_function, matlab_snippet,
        json_plan, why_needed, expected_outputs, and qc_risks.
    """
    generators = {
        "RAW_T1_READY": _plan_segmentation,
        "SEGMENTATION_COMPLETED": _plan_dartel_import,
        "DARTEL_INPUT_READY": _plan_dartel_run,
        "DARTEL_COMPLETED": _plan_normalize,
        "NORMALIZATION_COMPLETED": _plan_smoothing,
        "SMOOTHING_COMPLETED": _plan_statistics_note,
        "VBM_READY_FOR_STATISTICS": _plan_statistics_note,
        "INCOMPLETE_OR_ERROR": _plan_error,
    }

    generator = generators.get(state)
    if generator is None:
        return {
            "status": "error",
            "message": (
                f"Unknown state: '{state}'. "
                f"Expected one of: {list(generators.keys())}"
            ),
        }

    return generator(input_files)


def _plan_segmentation(input_files):
    t1 = input_files.get("t1", "/path/to/T1.nii")
    return {
        "status": "success",
        "step_name": "Tissue Segmentation",
        "spm_function": "spm.spatial.preproc",
        "why_needed": (
            "Segmentation separates the T1 image into gray matter, white matter, and CSF "
            "probability maps. Every downstream VBM step depends on these maps being "
            "accurate -- they are the raw material for all normalization, modulation, "
            "and smoothing steps that follow."
        ),
        "expected_outputs": [
            "c1T1.nii (gray matter probability map, 0 to 1 per voxel)",
            "c2T1.nii (white matter probability map)",
            "c3T1.nii (CSF probability map)",
            "y_T1.nii (forward deformation field to MNI space)",
            "mT1.nii (bias-corrected version of the input T1)",
        ],
        "qc_risks": [
            "Check that c1T1.nii overlays cleanly onto gray matter in the original T1 -- it should not bleed into skull or white matter.",
            "Verify c3T1.nii highlights ventricles and sulci, not random patches inside the brain.",
            "A strong uncorrected bias field can misclassify large brain regions.",
            "Very young, very old, or atypical brains may not match the SPM adult template priors well.",
        ],
        "matlab_snippet": (
            f"spm('defaults', 'fmri');\n"
            f"spm_jobman('initcfg');\n"
            f"\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.channel.vols = {{'{t1},1'}};\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.channel.biasreg = 0.001;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.channel.biasfwhm = 60;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.channel.write = [0 1];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(1).tpm = {{fullfile(spm('dir'),'tpm','TPM.nii,1')}};\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(1).ngaus = 1;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(1).native = [1 1];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(2).tpm = {{fullfile(spm('dir'),'tpm','TPM.nii,2')}};\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(2).ngaus = 1;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(2).native = [1 1];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(3).tpm = {{fullfile(spm('dir'),'tpm','TPM.nii,3')}};\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(3).ngaus = 2;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.tissue(3).native = [1 0];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.mrf = 1;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.cleanup = 1;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.reg = [0 0.001 0.5 0.05 0.2];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.affreg = 'mni';\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.fwhm = 0;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.samp = 3;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.write = [0 1];\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.vox = NaN;\n"
            f"matlabbatch{{1}}.spm.spatial.preproc.warp.bb = [NaN NaN NaN; NaN NaN NaN];\n"
            f"\n"
            f"spm_jobman('run', matlabbatch);"
        ),
        "json_plan": {
            "step_name": "Tissue Segmentation",
            "spm_function": "spm.spatial.preproc",
            "input_files": {"t1_image": t1},
            "parameters": {
                "num_tissues": 6,
                "bias_regularisation": 0.001,
                "bias_fwhm": 60,
                "write_bias_corrected": True,
                "write_deformation_fields": [False, True],
                "mrf_cleanup": True,
                "affine_regularisation": "mni",
            },
            "expected_outputs": [
                "c1T1.nii", "c2T1.nii", "c3T1.nii", "y_T1.nii", "mT1.nii"
            ],
        },
    }


def _plan_dartel_import(input_files):
    c1 = input_files.get("c1", "/path/to/c1T1.nii")
    c2 = input_files.get("c2", "/path/to/c2T1.nii")
    return {
        "status": "success",
        "step_name": "DARTEL Import",
        "spm_function": "spm.tools.dartel.impo",
        "why_needed": (
            "DARTEL import rigidly aligns each subject's tissue maps to a common starting "
            "position before the iterative DARTEL warp. Without this step, subjects with "
            "different head positions in the scanner would not converge on a stable group "
            "template during alignment."
        ),
        "expected_outputs": [
            "rc1T1.nii (rigidly aligned gray matter, ready for DARTEL)",
            "rc2T1.nii (rigidly aligned white matter, ready for DARTEL)",
        ],
        "qc_risks": [
            "If the rigid alignment looks off in one subject, that subject will pull the group template toward its position.",
            "Check that rc1T1.nii and rc2T1.nii overlap sensibly with each other and with the same files from other subjects.",
        ],
        "matlab_snippet": (
            f"matlabbatch{{1}}.spm.tools.dartel.impo.files{{1}} = {{'{c1},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.impo.files{{2}} = {{'{c2},1'}};\n"
            f"\n"
            f"spm_jobman('run', matlabbatch);"
        ),
        "json_plan": {
            "step_name": "DARTEL Import",
            "spm_function": "spm.tools.dartel.impo",
            "input_files": {"c1": c1, "c2": c2},
            "parameters": {},
            "expected_outputs": ["rc1T1.nii", "rc2T1.nii"],
        },
    }


def _plan_dartel_run(input_files):
    rc1 = input_files.get("rc1", "/path/to/rc1T1.nii")
    rc2 = input_files.get("rc2", "/path/to/rc2T1.nii")
    return {
        "status": "success",
        "step_name": "DARTEL Alignment",
        "spm_function": "spm.tools.dartel.warp",
        "why_needed": (
            "DARTEL builds a study-specific group template by iteratively warping all subjects "
            "toward each other. The resulting flow fields capture each subject's unique shape "
            "relative to the group average, which is more accurate than warping directly to "
            "a generic MNI template."
        ),
        "expected_outputs": [
            "u_rc1T1.nii (subject-specific DARTEL flow field)",
            "Template_0.nii through Template_6.nii (iterative group templates)",
        ],
        "qc_risks": [
            "DARTEL needs at least 20 subjects to build a stable template -- smaller groups produce poor warps.",
            "Check Template_6.nii visually -- it should look like a blurry but recognizable brain.",
            "Any subject whose overlay on the final template looks noisy should be investigated for upstream segmentation errors.",
        ],
        "matlab_snippet": (
            f"matlabbatch{{1}}.spm.tools.dartel.warp.images{{1}} = {{'{rc1},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.images{{2}} = {{'{rc2},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.template = 'Template';\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.rform = 0;\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.param(1).its = 3;\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.param(1).rparam = [4 2 1e-06];\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.param(6).its = 3;\n"
            f"matlabbatch{{1}}.spm.tools.dartel.warp.settings.param(6).rparam = [0.25 0.125 1e-06];\n"
            f"\n"
            f"spm_jobman('run', matlabbatch);"
        ),
        "json_plan": {
            "step_name": "DARTEL Alignment",
            "spm_function": "spm.tools.dartel.warp",
            "input_files": {"rc1": rc1, "rc2": rc2},
            "parameters": {
                "iterations": 6,
                "regularisation_form": "linear_elastic",
            },
            "expected_outputs": [
                "u_rc1T1.nii",
                "Template_0.nii",
                "Template_1.nii",
                "Template_2.nii",
                "Template_3.nii",
                "Template_4.nii",
                "Template_5.nii",
                "Template_6.nii",
            ],
        },
    }


def _plan_normalize(input_files):
    flow_field = input_files.get("flow_field", "/path/to/u_rc1T1.nii")
    rc1 = input_files.get("rc1", "/path/to/rc1T1.nii")
    return {
        "status": "success",
        "step_name": "Normalize to MNI Space",
        "spm_function": "spm.tools.dartel.mni_norm",
        "why_needed": (
            "Normalization uses each subject's DARTEL flow field to warp their tissue maps "
            "into MNI standard space. Without this step every subject's brain sits in its "
            "own native coordinate system, making voxel-by-voxel comparison across subjects "
            "meaningless."
        ),
        "expected_outputs": [
            "wc1T1.nii (warped gray matter in MNI space)",
            "wc2T1.nii (warped white matter in MNI space)",
            "mwc1T1.nii (modulated warped gray matter, volume-preserving)",
        ],
        "qc_risks": [
            "Overlay wc1T1.nii on the MNI template and check that major landmarks align -- cortex outline, ventricles, brainstem.",
            "Compare warped images across subjects -- they should look broadly similar since they are all in the same space.",
            "Watch for extreme local distortions in the cerebellum or ventral brain regions.",
        ],
        "matlab_snippet": (
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.template = {{'{flow_field},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.data.subj.flowfield = {{'{flow_field},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.data.subj.images = {{'{rc1},1'}};\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.vox = [1.5 1.5 1.5];\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.bb = [NaN NaN NaN; NaN NaN NaN];\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.preserve = 1;\n"
            f"matlabbatch{{1}}.spm.tools.dartel.mni_norm.fwhm = [0 0 0];\n"
            f"\n"
            f"spm_jobman('run', matlabbatch);"
        ),
        "json_plan": {
            "step_name": "Normalize to MNI Space",
            "spm_function": "spm.tools.dartel.mni_norm",
            "input_files": {"flow_field": flow_field, "rc1": rc1},
            "parameters": {
                "voxel_size": [1.5, 1.5, 1.5],
                "preserve_amounts": True,
                "modulate": True,
                "smoothing_fwhm": [0, 0, 0],
            },
            "expected_outputs": ["wc1T1.nii", "wc2T1.nii", "mwc1T1.nii"],
        },
    }


def _plan_smoothing(input_files):
    mwc1 = input_files.get("mwc1", input_files.get("mwp1", "/path/to/mwc1T1.nii"))
    return {
        "status": "success",
        "step_name": "Gaussian Smoothing",
        "spm_function": "spm.spatial.smooth",
        "why_needed": (
            "Smoothing applies a Gaussian blur so each voxel reflects the weighted average "
            "of its neighbors. This compensates for residual misalignment after normalization "
            "and makes the data meet the smoothness assumptions required for Gaussian Random "
            "Field theory, which is the standard multiple-comparisons correction in VBM."
        ),
        "expected_outputs": [
            "smwc1T1.nii (smoothed modulated warped gray matter -- final input to statistics)",
            "smwc2T1.nii (smoothed modulated warped white matter)",
        ],
        "qc_risks": [
            "A kernel larger than 10mm blurs out small focal effects, especially in subcortical structures like the hippocampus.",
            "Compare smwc1T1.nii and mwc1T1.nii side by side -- the smoothed version should look like a blurred copy of the modulated one.",
            "Make sure the FWHM used matches what you plan to report in your methods section.",
        ],
        "matlab_snippet": (
            f"matlabbatch{{1}}.spm.spatial.smooth.data = {{'{mwc1},1'}};\n"
            f"matlabbatch{{1}}.spm.spatial.smooth.fwhm = [8 8 8];\n"
            f"matlabbatch{{1}}.spm.spatial.smooth.dtype = 0;\n"
            f"matlabbatch{{1}}.spm.spatial.smooth.im = 0;\n"
            f"matlabbatch{{1}}.spm.spatial.smooth.prefix = 's';\n"
            f"\n"
            f"spm_jobman('run', matlabbatch);"
        ),
        "json_plan": {
            "step_name": "Gaussian Smoothing",
            "spm_function": "spm.spatial.smooth",
            "input_files": {"modulated_warped_gm": mwc1},
            "parameters": {
                "fwhm": [8, 8, 8],
                "data_type": "same_as_input",
                "implicit_masking": False,
                "prefix": "s",
            },
            "expected_outputs": ["smwc1T1.nii", "smwc2T1.nii"],
        },
    }


def _plan_statistics_note(input_files):
    return {
        "status": "success",
        "step_name": "Second-Level Statistical Analysis",
        "spm_function": "spm.stats.factorial_design",
        "why_needed": (
            "With preprocessing complete, the smoothed modulated warped gray matter maps "
            "are stacked across all subjects and a voxel-wise GLM is run to test for group "
            "differences or correlations with variables of interest. This is the step that "
            "produces the actual scientific results."
        ),
        "expected_outputs": [
            "SPM.mat (full analysis object: design matrix, contrasts, and results)",
            "beta_*.nii (estimated effect size at each voxel, one file per regressor)",
            "spmT_*.nii (t-statistic maps for each contrast)",
            "spmF_*.nii (F-statistic maps for F-contrasts)",
        ],
        "qc_risks": [
            "Always include total intracranial volume (TIV) as a covariate -- without it, head size differences will mimic group differences.",
            "Report FWE or FDR corrected results. Uncorrected p-values across hundreds of thousands of voxels produce thousands of false positives.",
            "Check the design matrix visually before running -- it should show clean group structure with no confounded columns.",
            "Make sure contrast signs are correct. A reversed sign gives a real-looking result that tests the opposite hypothesis.",
        ],
        "matlab_snippet": (
            "% Second-level analysis -- no automatic script generated.\n"
            "% The design matrix depends on your study groups, covariates, and contrasts.\n"
            "% Set this up manually in SPM's GUI or write a custom batch based on\n"
            "% your specific hypotheses.\n"
            "%\n"
            "% Required inputs: all subjects' smwc1*.nii files, TIV estimates,\n"
            "% group labels, and any additional covariates (age, sex, etc.)."
        ),
        "json_plan": {
            "step_name": "Second-Level Statistical Analysis",
            "spm_function": "spm.stats.factorial_design",
            "input_files": {"smoothed_gm_maps": "smwc1*.nii for all subjects"},
            "parameters": {
                "model": "GLM",
                "recommended_covariates": ["total_intracranial_volume", "age", "sex"],
                "correction": "FWE or FDR",
                "note": "Design is study-specific. No default parameters are provided.",
            },
            "expected_outputs": ["SPM.mat", "beta_*.nii", "spmT_*.nii", "spmF_*.nii"],
        },
    }


def _plan_error(input_files):
    return {
        "status": "error",
        "message": (
            "The folder is in an INCOMPLETE_OR_ERROR state. The pipeline state is "
            "inconsistent -- later-stage files exist without the expected earlier-stage files. "
            "Investigate what files are present and whether any were accidentally deleted or "
            "moved before generating a new plan."
        ),
    }
