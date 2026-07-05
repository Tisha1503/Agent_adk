import os
import glob
import shutil
import subprocess
from datetime import datetime

_MATLAB_GLOB = r"C:\Program Files\MATLAB\*\bin\matlab.exe"
_DEFAULT_TIMEOUT_SECONDS = 3600
_LOG_TAIL_CHARS = 3000


def _find_matlab():
    exe = shutil.which("matlab")
    if exe:
        return exe
    candidates = sorted(glob.glob(_MATLAB_GLOB), reverse=True)
    if candidates:
        return candidates[0]
    return None


def _tail(text, limit=_LOG_TAIL_CHARS):
    if text is None:
        return ""
    if len(text) <= limit:
        return text
    return text[-limit:]


def save_spm_batch(matlab_snippet: str, output_path: str) -> dict:
    """Write a draft SPM MATLAB snippet to a .m file on disk.

    Use this to persist the matlab_snippet produced by
    generate_spm_batch_template before running it. The resulting .m file can
    then be passed to run_spm_batch.

    Args:
        matlab_snippet: The MATLAB/SPM batch code as a string.
        output_path: Where to write the file. If it does not end in '.m',
                     the extension is added automatically.

    Returns:
        A dict with status and the absolute path of the written script.
    """
    if not matlab_snippet or not matlab_snippet.strip():
        return {"status": "error", "message": "matlab_snippet is empty, nothing to write."}

    if not output_path.endswith(".m"):
        output_path = output_path + ".m"

    try:
        folder = os.path.dirname(os.path.abspath(output_path))
        if folder and not os.path.isdir(folder):
            os.makedirs(folder, exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as handle:
            handle.write(matlab_snippet)
    except OSError as error:
        return {"status": "error", "message": f"Could not write script: {error}"}

    return {
        "status": "success",
        "batch_file": os.path.abspath(output_path),
        "message": f"Batch script written to {os.path.abspath(output_path)}.",
    }


def run_spm_batch(batch_file: str, expected_outputs: list = None, check_folder: str = "") -> dict:
    """Run an SPM MATLAB batch script, save the log, and verify outputs.

    This is the optional execution wrapper. It only runs when you explicitly
    ask to execute a step. It launches MATLAB in non-interactive batch mode,
    saves the full command log next to the script, and then checks whether the
    expected output files were produced.

    MATLAB must be installed and SPM must be on the MATLAB path for this to
    succeed. If MATLAB cannot be found, a clean error dict is returned instead
    of crashing.

    Args:
        batch_file: Path to a .m SPM batch script (see save_spm_batch).
        expected_outputs: Optional list of filename patterns to look for after
                          the run, e.g. ['rc1*.nii', 'rc2*.nii'].
        check_folder: Folder to search for expected outputs. Defaults to the
                      folder containing the batch script.

    Returns:
        A dict with status, return_code, log_file, stdout/stderr tails, and the
        results of the expected-output check.
    """
    batch_file = os.path.abspath(batch_file)
    if not os.path.isfile(batch_file):
        return {"status": "error", "message": f"Batch file not found: {batch_file}"}

    matlab_exe = _find_matlab()
    if matlab_exe is None:
        return {
            "status": "error",
            "message": (
                "MATLAB executable not found. Install MATLAB or add it to PATH. "
                "The plan can still be reviewed in dry-run mode without running it."
            ),
        }

    if not check_folder:
        check_folder = os.path.dirname(batch_file)

    script_dir = os.path.dirname(batch_file)
    script_stem = os.path.splitext(os.path.basename(batch_file))[0]
    run_command = "run('" + batch_file.replace("\\", "/") + "')"
    command = [matlab_exe, "-batch", run_command]

    started = datetime.now()
    try:
        completed = subprocess.run(
            command,
            cwd=check_folder if os.path.isdir(check_folder) else script_dir,
            capture_output=True,
            text=True,
            timeout=_DEFAULT_TIMEOUT_SECONDS,
        )
        return_code = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
        timed_out = False
    except subprocess.TimeoutExpired as error:
        return_code = None
        stdout = error.stdout if isinstance(error.stdout, str) else ""
        stderr = (error.stderr if isinstance(error.stderr, str) else "") + \
            f"\nTimed out after {_DEFAULT_TIMEOUT_SECONDS} seconds."
        timed_out = True

    log_path = os.path.join(script_dir, script_stem + "_run.log")
    try:
        with open(log_path, "w", encoding="utf-8") as handle:
            handle.write(f"SPM batch run log\n")
            handle.write(f"Started: {started.isoformat()}\n")
            handle.write(f"Finished: {datetime.now().isoformat()}\n")
            handle.write(f"MATLAB: {matlab_exe}\n")
            handle.write(f"Command: {' '.join(command)}\n")
            handle.write(f"Return code: {return_code}\n")
            handle.write("\n===== STDOUT =====\n")
            handle.write(stdout or "")
            handle.write("\n===== STDERR =====\n")
            handle.write(stderr or "")
    except OSError:
        log_path = None

    outputs_found = []
    outputs_missing = []
    if expected_outputs:
        for pattern in expected_outputs:
            hits = glob.glob(os.path.join(check_folder, pattern))
            if hits:
                outputs_found.append(pattern)
            else:
                outputs_missing.append(pattern)

    run_ok = (return_code == 0) and not timed_out
    outputs_ok = (not expected_outputs) or (len(outputs_missing) == 0)

    if run_ok and outputs_ok:
        status = "success"
        message = "Batch ran and all expected outputs were found."
    elif run_ok and not outputs_ok:
        status = "error"
        message = (
            "Batch returned success but some expected outputs are missing. "
            "Check the log and confirm SPM was on the MATLAB path."
        )
    else:
        status = "error"
        message = (
            "Batch run failed or timed out. Check the log for the MATLAB error. "
            "A common cause is SPM not being on the MATLAB path."
        )

    return {
        "status": status,
        "message": message,
        "batch_file": batch_file,
        "matlab_executable": matlab_exe,
        "return_code": return_code,
        "timed_out": timed_out,
        "log_file": log_path,
        "check_folder": check_folder,
        "stdout_tail": _tail(stdout),
        "stderr_tail": _tail(stderr),
        "expected_outputs_checked": expected_outputs or [],
        "outputs_found": outputs_found,
        "outputs_missing": outputs_missing,
        "all_outputs_present": outputs_ok,
    }
