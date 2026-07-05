# Week 4 - Automated VBM Workflow Agent

This week turns the Week 3 VBM knowledge into a working agent. Given a subject
folder, the agent figures out how far the VBM pipeline has progressed, decides
the next preprocessing step, and produces a draft SPM plan explaining what to
run and why. It runs in dry-run mode by default, so it shows the plan and never
executes SPM on its own.

## What it does

1. Scans a subject folder and classifies it into a formal pipeline state.
2. Reports which files were found and what is missing for the next step.
3. Generates the next-step plan as both a draft MATLAB/SPM snippet and a
   structured JSON plan.
4. Explains why the next step matters, not just the command to run.
5. Lists the output files to expect and the QC risks to check visually.

Both naming conventions are supported: SPM-DARTEL (c1/wc1/mwc1/smwc1) and
CAT12 (p1/wp1/mwp1/smwp1).

## Files

| File | Purpose |
|---|---|
| `my_agent/vbm_state_detectorW4.py` | `detect_vbm_state(folder_path)` - classifies a folder into a pipeline state |
| `my_agent/spm_batch_template_generatorW4.py` | `generate_spm_batch_template(state, input_files)` - draft next-step plan |
| `my_agent/vbm_workflow_statesW4.json` | Reference definition of all 8 states and their transitions |
| `my_agent/agent.py` | ADK agent that wires the tools together |
| `example_dry_runW4.json` | Sample dry-run output on the test folder |
| `example_agent_responseW4.md` | Sample agent response for a status question |
| `test_vbm_subject/` | Dummy subject folder (T1 + c1/c2/c3) for testing |

## The 8 workflow states

| State | Meaning |
|---|---|
| `RAW_T1_READY` | Only a raw T1w image exists. Pipeline has not started. |
| `SEGMENTATION_COMPLETED` | Gray matter, white matter, and CSF maps exist. |
| `DARTEL_INPUT_READY` | rc1/rc2 rigidly aligned maps exist. |
| `DARTEL_COMPLETED` | Flow fields and study templates exist. |
| `NORMALIZATION_COMPLETED` | Warped (and possibly modulated) MNI maps exist. |
| `SMOOTHING_COMPLETED` | Smoothed maps exist but earlier files not fully verified. |
| `VBM_READY_FOR_STATISTICS` | Full pipeline complete, all prerequisites verified. |
| `INCOMPLETE_OR_ERROR` | Later-stage files exist without expected earlier files. |

## The two tools

### detect_vbm_state(folder_path)

Scans the folder, checks for T1w input and output files from each step in
reverse pipeline order, and validates logical consistency. Returns a dict with:

- `detected_state` and `state_description`
- `found_files` (matched pattern to file list)
- `input_t1_found` and `input_t1_files`
- `missing_for_next_step`
- `summary` in plain English

### generate_spm_batch_template(state, input_files)

Takes a state and a dict of input file paths, returns the next-step plan:

- `matlab_snippet` - a draft SPM batch script with input files filled in
- `json_plan` - structured plan with spm_function, parameters, expected_outputs
- `why_needed`, `expected_outputs`, and `qc_risks`

Sensible defaults are built in, for example 6 tissue classes for segmentation
and an 8mm FWHM smoothing kernel.

## How to run

The agent runs on Google ADK with a free OpenRouter model.

```powershell
conda activate adk
cd "path\to\Neuro_claw_agent"
adk web
```

Open the printed URL (usually http://localhost:8000), select `my_agent`, and
ask a question. To use the terminal instead of the browser:

```powershell
adk run my_agent
```

## Example prompt

```
What's the VBM status for test_vbm_subject and what should I do next?
```

The agent calls `detect_vbm_state` (reports SEGMENTATION_COMPLETED), then
`generate_spm_batch_template` (next step is DARTEL import), and explains why
the step is needed, what files to expect, and what to check visually.

## Design notes

- Every tool returns a dict with a `status` field of `success` or `error`.
- Every tool has a docstring, which ADK reads as the tool description.
- Bad paths and missing folders return clean error dicts and never crash.
- Dry-run by default: the agent shows the plan and never runs SPM automatically.
