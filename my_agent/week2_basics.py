import os
import numpy as np
import nibabel as nib


# (1) .nii and .nii.gz files

# saving as uncompressed (.nii) using nibabel
nib.save(img, "brain.nii")

# saving as compressed (.nii.gz) using nibabel 
nib.save(img, "brain.nii.gz")

# load the images(This works similary for both formats)

img = nib.load("brain.nii")
img = nib.load("brain.nii.gz")

#---------------------------------------------------------------------------------------------------

# (2) conversions

# PART I: DICOM to NIfTI

# option A: command line tool (install: conda install -c conda-forge dcm2niix)
# dcm2niix -o output_folder -f subject01 input_dicom_folder

# option B: Python
import dicom2nifti

dicom2nifti.convert_directory(
    "input_dicom_folder",
    "output_folder",
    compression=True
)

# Part II:  AFNI to NIfTI

# command line only (Linux/Mac, requires AFNI installed)
# 3dAFNItoNIFTI -prefix output_name input_dataset+orig

# Python: nibabel can read AFNI and save it again as NIfTI
afni_img = nib.load("dataset+orig.HEAD")
nib.save(afni_img, "dataset.nii.gz")

#------------------------------------------------------------------------------------------------------------

# 3. Load with nibabel

img  = nib.load("brain.nii.gz")   
data = img.get_fdata()             # loads the voxel array (.get_fdata())


# 4
# Part I: Image shape

shape = img.shape                  # Outputs something like (256, 256, 176) — voxels per axis

# number of dimensions: 3 for T1w, 4 for fMRI
ndim  = data.ndim                  


#Part II:  Voxel spacing

zooms = img.header.get_zooms()     # something like (1.0, 1.0, 1.0) mm
zooms_spatial = zooms[:3]          #  we drop 4th value (time step) if 4D image


# PART III: Affine matrix

affine = img.affine                # 4x4 numpy array, voxel -> world (mm) map

# what each part does:
# top-left 3x3  = voxel size + rotation
# diagonal [0,0],[1,1],[2,2] = voxel sizes in mm
# last column [0:3, 3]       = origin (where voxel 0,0,0 sits in mm)

# convert a single voxel coordinate to world mm
voxel_coord = np.array([128, 109, 88, 1])      # i, j, k, 1
world_coord  = affine @ voxel_coord             # x, y, z in mm


# Part IV: Orientation

# derive orientation code from the affine
codes = nib.aff2axcodes(img.affine)            #  ('R', 'A', 'S')

# each letter says which direction that axis increases toward:
# R/L = Right/Left,  A/P = Anterior/Posterior,  S/I = Superior/Inferior

# We check for a left-right flip (the silent error):
if codes[0] == 'L':
    print("Warning: first axis points Left — possible orientation flip")


# 5. Check whether image is valid for VBM / FreeSurfer

shape = img.shape
zooms = img.header.get_zooms()[:3]

# must be 3D (4D = fMRI time series, incorrect modality)
is_3d = data.ndim == 3

# voxels should be near 1mm isotropic (both tools assume this)
is_isotropic = max(zooms) / min(zooms) < 1.5
is_near_1mm  = all(abs(v - 1.0) < 0.5 for v in zooms)

# field of view should fit a whole brain (roughly 150-300mm per axis)
fov = [s * v for s, v in zip(shape, zooms)]
fov_ok = all(120 < f < 320 for f in fov)

# image should not be empty or corrupt
has_nan      = bool(np.isnan(data).any())
is_not_empty = data.max() > 0