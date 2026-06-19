# Why input image parameters matter for sMRI preprocessing

Before running any structural preprocessing, it's worth checking a few basic things about the image. Most of these checks take milliseconds, but skipping them is how you end up wasting hours of compute on data that was never going to work.

**Voxel size and isotropy.** VBM and FreeSurfer were both designed around T1w scans with roughly 1mm isotropic voxels. When the voxels are thicker in one direction, or just larger overall, the cost shows up downstream: cortical thickness gets noisy, surface reconstruction misses fine detail, and registration to a template loses accuracy. None of that fails loudly. It just quietly makes every later measurement less trustworthy, so it's much easier to catch this from the header before the pipeline starts.

**Image dimensionality.** A T1w scan should be a single 3D volume. A 4D shape is almost always fMRI passed in by mistake, since the fourth dimension is time. If you don't catch this up front, VBM will fail somewhere deep in SPM with an unhelpful error. A simple `ndim == 3` check at the door catches it instantly and lets the agent say what's actually wrong.

**Affine and orientation.** The affine matrix is what ties the voxel grid to real anatomical space. A bad affine breaks registration to MNI, which means every voxel-wise comparison across subjects is comparing the wrong places. Orientation is the worst case to miss: an L/R-flipped image still looks like a normal brain, nothing errors, the pipeline runs to completion, and every result is on the wrong hemisphere. The header is the only place to catch this cheaply.

**Content sanity.** NaN values, all-zero images, and unusually high zero-voxel ratios all point to the same thing: corruption, a failed conversion, or a truncated file. These are some of the simplest checks to write and the most expensive ones to skip, because a single NaN propagates into every statistic that touches it.

Header-only inspection like this catches the most expensive errors at the front door, before any pipeline runs. It can't tell you whether a scan has motion or imaging artifacts, only whether the geometry and content look usable, so the verdict should always be clear about that scope.
