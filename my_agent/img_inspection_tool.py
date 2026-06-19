import os
import tempfile
import numpy as np
import nibabel as nib
import dicom2nifti


def load_as_nifti(path: str):
    if os.path.isdir(path):
        output_dir = tempfile.mkdtemp()
        dicom2nifti.convert_directory(path, output_dir, compression=True, reorient=True)
        converted = [f for f in os.listdir(output_dir) if f.endswith((".nii", ".nii.gz"))]
        if not converted:
            raise ValueError(f"No NIfTI output produced from DICOM directory: {path}")
        return nib.load(os.path.join(output_dir, converted[0]))

    if path.endswith(".HEAD") or path.endswith(".BRIK") or path.endswith(".BRIK.gz"):
        afni_img = nib.load(path)
        nifti_path = os.path.join(tempfile.mkdtemp(), "converted.nii.gz")
        nib.save(afni_img, nifti_path)
        return nib.load(nifti_path)

    if path.endswith(".nii") or path.endswith(".nii.gz"):
        return nib.load(path)

    raise ValueError(f"Unrecognised image format for path: {path}")


def inspect_t1_image(path: str) -> dict:
    try:
        img = load_as_nifti(path)
        data = img.get_fdata()
    except Exception as e:
        return {"status": "error", "message": f"Could not read image: {e}"}

    return {
        "status": "success",
        "shape": list(data.shape),
        "voxel_size_mm": [round(float(v), 4) for v in img.header.get_zooms()[:3]],
        "affine": img.affine.tolist(),
        "orientation": list(nib.aff2axcodes(img.affine)),
        "is_3d": data.ndim == 3,
        "has_nan": bool(np.isnan(data).any()),
        "intensity": {
            "min": float(np.nanmin(data)),
            "max": float(np.nanmax(data)),
            "mean": round(float(np.nanmean(data)), 4),
        },
        "zero_voxel_ratio": round(float(np.sum(data == 0) / data.size), 4),
    }


def validate_for_preprocessing(path: str) -> dict:
    try:
        img = load_as_nifti(path)
        data = img.get_fdata()
    except Exception as e:
        return {"status": "error", "message": f"Could not read image: {e}"}

    shape = img.shape
    zooms = img.header.get_zooms()[:3]
    codes = nib.aff2axcodes(img.affine)

    is_3d = data.ndim == 3
    is_isotropic = bool(max(zooms) / min(zooms) < 1.5)
    is_near_1mm = all(abs(v - 1.0) < 0.5 for v in zooms)

    fov = [s * v for s, v in zip(shape, zooms)]
    fov_ok = all(120 < f < 320 for f in fov)

    has_nan = bool(np.isnan(data).any())
    is_not_empty = bool(data.max() > 0)

    orientation_flip_warning = codes[0] == "L"

    is_valid = (
        is_3d
        and is_isotropic
        and is_near_1mm
        and fov_ok
        and not has_nan
        and is_not_empty
    )

    return {
        "status": "success",
        "is_3d": is_3d,
        "is_isotropic": is_isotropic,
        "is_near_1mm": is_near_1mm,
        "fov_mm": [round(float(f), 2) for f in fov],
        "fov_ok": fov_ok,
        "has_nan": has_nan,
        "is_not_empty": is_not_empty,
        "orientation_flip_warning": orientation_flip_warning,
        "is_valid": is_valid,
    }
