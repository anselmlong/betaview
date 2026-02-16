# BetaView Heuristics (Backend)

BetaView intentionally uses **simple, explainable heuristics** computed from 2D pose keypoints (MediaPipe Pose) to approximate technique quality.

Because the input is a monocular 2D video, some quantities described in the literature (e.g., *true* hip-to-wall distance in cm) cannot be measured directly; BetaView either:
- computes a **2D proxy** (pixels / ratios), or
- reports the metric as **"best-effort"** and uses it primarily for coaching feedback.

## Implemented heuristics

### 1) Path efficiency ("geometric entropy" style)
**What:** ratio of direct start→end hip displacement to total hip path length.

**Why:** A more direct hip trajectory indicates more deliberate, efficient climbing.

**Implementation:** `direct_distance / total_distance` using the mid-hip trajectory.

### 2) Trajectory entropy (movement variability)
**What:** Shannon entropy (normalized 0–1) of the **direction distribution** of consecutive hip displacement vectors.

**Why:** Higher variability is a proxy for "wandering" or frequent direction changes; lower entropy indicates a more repeatable, consistent motion strategy.

**Implementation:** bin displacement directions into 8 bins, compute normalized Shannon entropy.

**Source:** framing inspired by movement-variability / entropy discussion in the University of Leeds climbing biomechanics thesis.

### 3) Straight arms / relaxed shoulders (joint-angle thresholds)
**What:** fraction of frames where:
- **Elbow angle** (shoulder–elbow–wrist) is open (>= 150°)
- **Shoulder angle** (elbow–shoulder–hip) is open (>= 150°)

**Why:** Straight-arm climbing and post-move shoulder relaxation are commonly coached for energy efficiency and avoiding over-gripping.

**Implementation:** compute joint angles from 2D keypoints; report ratios.

**Source:** joint-angle thresholds and the 150° criterion are taken from the skeleton-video-stream climbing evaluation approach in Sensors (MDPI) 2023.

### 4) Reaching time ("reaching hand supports")
**What:** detect "reach" segments from wrist speed and compute:
- average reach duration
- count of reaches > 1.0s

**Why:** Long reaches can indicate hesitation or poor use of the supporting hand.

**Implementation:** segment wrist motion where speed exceeds a threshold; measure duration.

**Source:** reaching-time (>1s) heuristic from Sensors (MDPI) 2023.

### 5) CoM / hip smoothness (BMC-style CoM trajectory analysis)
**What:** a bounded (0–1) smoothness score derived from the mean **jerk** magnitude of the hip trajectory.

**Why:** smoother body-mass-center motion is associated with controlled movement and stable positioning.

**Implementation:** compute discrete derivatives of hip position (via timestamps) to estimate jerk; map mean jerk to `1 / (1 + jerk/scale)`.

**Source:** inspired by center-of-mass trajectory analysis approaches discussed in BMC-published work on climbing/body-mass-center movement.

## Citations

- Testa et al., *Climbing Technique Evaluation by Means of Skeleton Video Stream Analysis*, **Sensors** (MDPI), 2023, 23(19):8216. URL: https://pmc.ncbi.nlm.nih.gov/articles/PMC10574944/
- University of Leeds, *Climbing Biomechanics PhD Thesis*, 2005 (PDF in `research/Leeds_Climbing_Biomechanics_PhD_2005.pdf`).
- BMC (BioMed Central) paper PDF in `research/Body_Mass_Center_Climbing.pdf` (used for the CoM trajectory/smoothness framing).

## Where this lives in code

- Backend metric computation: `backend/heuristics.py`
- API job pipeline: `backend/main.py`
- Coaching prompt + frontend formatting: `backend/coach.py`
