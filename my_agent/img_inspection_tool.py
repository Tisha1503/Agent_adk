import numpy as np
import nibabel as nib


def inspect_t1_image(path: str) -> dict:
    img = nib.load(path)
    data = img.get_fdata()

    return {
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
