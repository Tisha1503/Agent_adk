def get_preprocessing_steps(modality: str) -> dict:
    pipelines = {
        "T1": {
            "modality": "T1-weighted sMRI",
            "steps": [
                "1. Format conversion (DICOM → NIfTI)",
                "2. Brain extraction / skull stripping (like FSL BET)",
                "3. Bias field correction (e.g. N4ITK)",
                "4. Tissue segmentation — GM / WM / CSF",
                "5. Registration to MNI152 standard space",
                "6. Spatial smoothing (typically 6–8 mm FWHM)",
            ],
            "notes": (
                "This is the core pipeline used in Voxel-Based Morphometry (VBM). "
                "Each step must be quality-checked before the next begins."
            ),
        },
        "VBM": {
            "modality": "Voxel-Based Morphometry (VBM)",
            "steps": [
                "1. Full T1 preprocessing (see T1 pipeline)",
                "2. Modulation of tissue segments by Jacobian determinant",
                "3. Statistical analysis with a General Linear Model (GLM)",
                "4. Multiple-comparison correction (FWE or FDR at cluster or voxel level)",
            ],
            "notes": (
                "VBM detects local differences in grey matter density across subjects or groups. "
                "Smoothing kernel size and registration quality have the biggest effect on results."
            ),
        },
        "FREESURFER": {
            "modality": "FreeSurfer Cortical Reconstruction",
            "steps": [
                "1. Motion correction and conform volume to 256³ isotropic",
                "2. Skull stripping (watershed + deformable surface)",
                "3. White matter segmentation",
                "4. Tessellation of the grey/white matter boundary",
                "5. Topology correction",
                "6. Surface inflation and registration to fsaverage atlas",
                "7. Cortical parcellation (Desikan-Killiany or Destrieux atlas)",
                "8. Morphological feature extraction: thickness, volume, area, curvature",
            ],
            "notes": (
                "FreeSurfer takes 6–12 hours per subject on a standard CPU. "
                "Outputs are used for ROI-based morphometry and connectomics."
            ),
        },
    }

    key = modality.strip().upper()
    if key in pipelines:
        return pipelines[key]

    return {
        "error": f"Unknown modality '{modality}'.",
        "supported": list(pipelines.keys()),
    }


def explain_concept(concept: str) -> dict:
    """
    Explains a key concept from the NeuroClaw paper or the Google ADK framework.

    Args:
        concept: Term to explain. Supported: 'agent', 'tool', 'skill',
                 'workflow', 'neuroclaw', 'smri', 'qc'.

    Returns:
        A dict with 'concept', 'definition', and 'example' keys, or an 'error'
        key if the concept is not recognised.
    """
    definitions = {
        "agent": {
            "concept": "Agent",
            "definition": (
                "An agent is an autonomous program that perceives inputs (user messages, "
                "tool results) and decides what actions to take to reach a goal. "
                "In Google ADK an agent is constructed with a name, a language model, "
                "a system instruction, and a list of callable tools."
            ),
            "example": (
                "A NeuroClaw agent receives 'Run VBM on subject_001' and autonomously "
                "decides to call skull-stripping, segmentation, and registration tools "
                "in the right order."
            ),
        },
        "tool": {
            "concept": "Tool",
            "definition": (
                "A tool is a plain Python function that an agent can invoke to do real work — "
                "run a shell command, read a file, query a database, or call an external API. "
                "The agent picks which tool to call and with what arguments based on context."
            ),
            "example": (
                "A 'run_bet' tool accepts the path to a T1 NIfTI file, calls FSL BET, "
                "and returns the path to the extracted brain mask."
            ),
        },
        "skill": {
            "concept": "Skill",
            "definition": (
                "A skill is a higher-level, reusable capability that bundles several tools "
                "and control-flow steps into one callable unit. "
                "A tool does one thing; a skill orchestrates several things."
            ),
            "example": (
                "A 'preprocess_t1' skill chains bias-correction → skull-stripping → "
                "registration and presents the agent with a single 'preprocess' action."
            ),
        },
        "workflow": {
            "concept": "Workflow",
            "definition": (
                "A workflow is the full end-to-end execution plan for a complex task. "
                "It links multiple skills and tools, handles branching, checkpointing, "
                "and verification so failures can be caught and recovered from."
            ),
            "example": (
                "NeuroClaw's neuroimaging workflow: ingest data → QC → preprocess "
                "→ analyse → generate report, with rollback if verification fails at any step."
            ),
        },
        "neuroclaw": {
            "concept": "NeuroClaw",
            "definition": (
                "NeuroClaw (CUHK-AIM) is a research project that wraps established "
                "neuroimaging tools (FSL, FreeSurfer, ANTs) as agent-callable tools and "
                "uses an LLM to orchestrate them end-to-end. "
                "Its strength is broad automation; its limitation is that it does not "
                "explain decisions, guide users, or perform reasoning-based QC."
            ),
            "example": (
                "A researcher types 'Analyse grey matter atrophy in this T1 cohort'; "
                "NeuroClaw selects the pipeline, calls each tool, logs results, "
                "and writes a report — with no human intervention."
            ),
        },
        "smri": {
            "concept": "Structural MRI (sMRI)",
            "definition": (
                "Structural MRI captures the 3D anatomy of the brain at high resolution. "
                "T1-weighted images are the most common type and are used to measure "
                "morphological features: volume, cortical thickness, surface area, "
                "and grey/white matter boundaries."
            ),
            "example": (
                "A T1 scan processed with FreeSurfer yields cortical thickness maps "
                "that can be compared across patient and control groups to find "
                "disease-related atrophy."
            ),
        },
        "qc": {
            "concept": "Quality Control (QC)",
            "definition": (
                "QC in neuroimaging is the process of checking that each preprocessing "
                "step produced anatomically correct, artifact-free results before "
                "the next step begins. Common failure modes: incomplete skull stripping, "
                "poor registration, motion artifacts, and segmentation leakage."
            ),
            "example": (
                "After BET, a QC tool checks that the brain mask fully covers the cortex "
                "and cerebellum without clipping — if it fails, preprocessing stops and "
                "flags the subject for manual review."
            ),
        },
    }

    key = concept.strip().lower()
    if key in definitions:
        return definitions[key]

    return {
        "error": f"Unknown concept '{concept}'.",
        "supported": list(definitions.keys()),
    }
