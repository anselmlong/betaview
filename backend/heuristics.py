"""BetaView Heuristics Engine

Calculates climbing technique metrics from pose data.

This module intentionally uses *simple, explainable heuristics* inspired by
published climbing-biomechanics and skeleton-analysis work.

Primary sources referenced in project docs:
- MDPI/Sensors 2023 skeleton video stream analysis (joint-angle thresholds,
  phase framing, reaching-time heuristic).
- University of Leeds (PhD thesis) movement-variability / entropy framing.
- BMC (Body/Center of Mass trajectory analysis) CoM smoothness framing.

Note: We only have 2D image-space keypoints from MediaPipe; some literature
features (e.g., true hip-to-wall distance in cm) are approximated in pixels or
via proxies.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple

import numpy as np


class Phase(Enum):
    STATIC = "static"
    MOVING = "moving"


@dataclass
class MovementPhase:
    """Represents a phase of movement (static or moving)."""

    phase_type: Phase
    start_frame: int
    end_frame: int
    duration_seconds: float


@dataclass
class SettleEvent:
    """Represents a foot placement settling event."""

    frame: int
    limb: str  # 'left_ankle' or 'right_ankle'
    jitter_score: float
    position: Tuple[float, float]


@dataclass
class ClimbMetrics:
    """Complete metrics for a climbing attempt."""

    # Existing BetaView metrics
    path_efficiency: float
    total_distance: float
    direct_distance: float
    move_count: int
    avg_pause_duration: float
    rhythm_variance: float
    avg_foot_jitter: float
    clean_placements: int
    total_placements: int
    stability_score: float
    body_tension_score: float
    sag_count: int
    climb_duration: float

    # Added: literature-inspired heuristics
    trajectory_entropy: float  # 0..1, higher = more varied/less repeatable path
    elbow_extension_ratio: float  # 0..1, higher = more straight arms (energy saving)
    shoulder_relax_ratio: float  # 0..1, higher = more open shoulder angle
    long_reach_count: int
    avg_reach_duration: float
    com_smoothness_score: float  # 0..1, higher = smoother CoM/hip motion

    def to_dict(self) -> dict:
        return {
            "path_efficiency": round(self.path_efficiency, 3),
            "total_distance": round(self.total_distance, 1),
            "direct_distance": round(self.direct_distance, 1),
            "move_count": int(self.move_count),
            "avg_pause_duration": round(self.avg_pause_duration, 2),
            "rhythm_variance": round(self.rhythm_variance, 3),
            "avg_foot_jitter": round(self.avg_foot_jitter, 2),
            "clean_placements": int(self.clean_placements),
            "total_placements": int(self.total_placements),
            "stability_score": round(self.stability_score, 3),
            "body_tension_score": round(self.body_tension_score, 3),
            "sag_count": int(self.sag_count),
            "climb_duration": round(self.climb_duration, 2),
            "trajectory_entropy": round(self.trajectory_entropy, 3),
            "elbow_extension_ratio": round(self.elbow_extension_ratio, 3),
            "shoulder_relax_ratio": round(self.shoulder_relax_ratio, 3),
            "long_reach_count": int(self.long_reach_count),
            "avg_reach_duration": round(self.avg_reach_duration, 2),
            "com_smoothness_score": round(self.com_smoothness_score, 3),
        }


# -----------------
# Basic geometry
# -----------------


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return float(np.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2))


def _angle_deg(
    a: Tuple[float, float], b: Tuple[float, float], c: Tuple[float, float]
) -> float:
    """Angle ABC in degrees, at point b."""

    ba = np.array([a[0] - b[0], a[1] - b[1]], dtype=float)
    bc = np.array([c[0] - b[0], c[1] - b[1]], dtype=float)

    nba = np.linalg.norm(ba)
    nbc = np.linalg.norm(bc)
    if nba < 1e-9 or nbc < 1e-9:
        return float("nan")

    cosang = float(np.dot(ba, bc) / (nba * nbc))
    cosang = max(-1.0, min(1.0, cosang))
    return float(np.degrees(np.arccos(cosang)))


def _shannon_entropy(probabilities: List[float]) -> float:
    """Shannon entropy in bits."""

    h = 0.0
    for p in probabilities:
        if p > 0:
            h -= p * math.log(p, 2)
    return h


# -----------------
# Existing metrics
# -----------------


def calculate_path_efficiency(
    hip_trajectory: List[Tuple[float, float]],
) -> Tuple[float, float, float]:
    """Geometric path efficiency (direct / total)."""

    if len(hip_trajectory) < 2:
        return 1.0, 0.0, 0.0

    total_distance = sum(
        euclidean_distance(hip_trajectory[i], hip_trajectory[i + 1])
        for i in range(len(hip_trajectory) - 1)
    )
    direct_distance = euclidean_distance(hip_trajectory[0], hip_trajectory[-1])

    if total_distance < 1e-6:
        return 1.0, 0.0, 0.0

    efficiency = direct_distance / total_distance
    return min(float(efficiency), 1.0), float(total_distance), float(direct_distance)


def calculate_velocities(
    trajectory: List[Tuple[float, float]], timestamps: List[float]
) -> List[float]:
    velocities: List[float] = []
    for i in range(len(trajectory) - 1):
        dt = timestamps[i + 1] - timestamps[i]
        if dt > 0:
            dist = euclidean_distance(trajectory[i], trajectory[i + 1])
            velocities.append(dist / dt)
        else:
            velocities.append(0.0)
    return velocities


def classify_movement_phases(
    velocities: List[float],
    timestamps: List[float],
    static_threshold: float = 15.0,  # pixels per second
) -> List[MovementPhase]:
    if not velocities:
        return []

    phases: List[MovementPhase] = []
    current_phase = Phase.STATIC if velocities[0] < static_threshold else Phase.MOVING
    phase_start = 0

    for i, vel in enumerate(velocities):
        new_phase = Phase.STATIC if vel < static_threshold else Phase.MOVING
        if new_phase != current_phase:
            duration = timestamps[i] - timestamps[phase_start] if timestamps else 0.0
            phases.append(
                MovementPhase(
                    phase_type=current_phase,
                    start_frame=phase_start,
                    end_frame=i - 1,
                    duration_seconds=float(duration),
                )
            )
            current_phase = new_phase
            phase_start = i

    if phase_start < len(velocities):
        duration = timestamps[-1] - timestamps[phase_start] if timestamps else 0.0
        phases.append(
            MovementPhase(
                phase_type=current_phase,
                start_frame=phase_start,
                end_frame=len(velocities) - 1,
                duration_seconds=float(duration),
            )
        )

    return phases


def analyze_rhythm(phases: List[MovementPhase]) -> Tuple[int, float, float]:
    moving_phases = [p for p in phases if p.phase_type == Phase.MOVING]
    static_phases = [p for p in phases if p.phase_type == Phase.STATIC]

    move_count = len(moving_phases)

    if static_phases:
        pause_durations = [p.duration_seconds for p in static_phases]
        avg_pause = float(np.mean(pause_durations))
        rhythm_variance = float(np.std(pause_durations))
    else:
        avg_pause = 0.0
        rhythm_variance = 0.0

    return int(move_count), avg_pause, rhythm_variance


def detect_settle_events(
    ankle_trajectories: Dict[str, List[Tuple[float, float]]],
    timestamps: List[float],
    settle_velocity_threshold: float = 10.0,
    min_settle_frames: int = 5,
) -> List[SettleEvent]:
    events: List[SettleEvent] = []

    for limb, trajectory in ankle_trajectories.items():
        if len(trajectory) < min_settle_frames + 10:
            continue

        velocities = calculate_velocities(trajectory, timestamps)

        i = 0
        while i < len(velocities) - min_settle_frames:
            if velocities[i] < settle_velocity_threshold:
                is_settle = all(
                    v < settle_velocity_threshold * 1.5
                    for v in velocities[i : i + min_settle_frames]
                )

                if is_settle:
                    post_settle_frames = min(
                        15, len(trajectory) - i - min_settle_frames
                    )
                    if post_settle_frames > 0:
                        post_positions = trajectory[
                            i + min_settle_frames : i
                            + min_settle_frames
                            + post_settle_frames
                        ]
                        if len(post_positions) > 1:
                            x_coords = [p[0] for p in post_positions]
                            y_coords = [p[1] for p in post_positions]
                            jitter = float(np.std(x_coords) + np.std(y_coords))
                        else:
                            jitter = 0.0

                        events.append(
                            SettleEvent(
                                frame=i,
                                limb=limb,
                                jitter_score=jitter,
                                position=trajectory[i],
                            )
                        )

                    i += min_settle_frames + 10
                    continue
            i += 1

    return events


def calculate_stability_score(
    settle_events: List[SettleEvent], jitter_threshold: float = 8.0
) -> Tuple[float, int, int]:
    if not settle_events:
        return 0.0, 0, 0

    jitter_scores = [e.jitter_score for e in settle_events]
    avg_jitter = float(np.mean(jitter_scores))
    clean_placements = int(sum(1 for j in jitter_scores if j < jitter_threshold))

    return avg_jitter, clean_placements, int(len(settle_events))


def calculate_body_tension(
    shoulder_positions: List[Tuple[float, float]],
    hip_positions: List[Tuple[float, float]],
) -> Tuple[float, int]:
    if len(shoulder_positions) != len(hip_positions) or len(shoulder_positions) < 10:
        return 1.0, 0

    alignments = [abs(s[0] - h[0]) for s, h in zip(shoulder_positions, hip_positions)]

    sag_threshold = float(np.mean(alignments) + np.std(alignments))
    sag_count = 0
    for i in range(1, len(alignments)):
        if alignments[i] > sag_threshold and alignments[i - 1] <= sag_threshold:
            sag_count += 1

    avg_offset = float(np.mean(alignments))

    all_x_coords = [s[0] for s in shoulder_positions] + [h[0] for h in hip_positions]
    frame_width_estimate = max(all_x_coords) if all_x_coords else 640.0
    max_expected_offset = frame_width_estimate * 0.15

    tension_score = max(0.0, 1.0 - (avg_offset / max_expected_offset))

    return float(tension_score), int(sag_count)


# -----------------
# Added heuristics
# -----------------


def calculate_trajectory_entropy(
    hip_trajectory: List[Tuple[float, float]],
    bins: int = 8,
) -> float:
    """Direction-distribution entropy of hip displacements (0..1).

    Higher entropy => more varied direction changes (less consistent / more wandering).

    This is a pragmatic "movement variability" proxy inspired by entropy framing used
    in climbing-biomechanics discussions (Leeds thesis).
    """

    if len(hip_trajectory) < 4:
        return 0.0

    angles: List[float] = []
    for i in range(len(hip_trajectory) - 1):
        dx = hip_trajectory[i + 1][0] - hip_trajectory[i][0]
        dy = hip_trajectory[i + 1][1] - hip_trajectory[i][1]
        if abs(dx) < 1e-6 and abs(dy) < 1e-6:
            continue
        angles.append(math.atan2(dy, dx))  # [-pi, pi]

    if len(angles) < 3:
        return 0.0

    # Bin angles uniformly
    counts = [0] * bins
    for a in angles:
        # map [-pi, pi] -> [0, 1)
        u = (a + math.pi) / (2 * math.pi)
        idx = min(bins - 1, int(u * bins))
        counts[idx] += 1

    total = sum(counts)
    if total == 0:
        return 0.0

    probs = [c / total for c in counts]
    h = _shannon_entropy(probs)
    h_max = math.log(bins, 2)
    return float(h / h_max) if h_max > 0 else 0.0


def _extract_point(
    keypoints: Dict[str, Tuple[float, float, float]],
    name: str,
    vis_threshold: float = 0.5,
) -> Optional[Tuple[float, float]]:
    p = keypoints.get(name)
    if not p:
        return None
    x, y, v = p
    if v < vis_threshold:
        return None
    return (float(x), float(y))


def calculate_joint_angle_ratios(
    pose_keypoints_per_frame: List[Dict[str, Tuple[float, float, float]]],
    elbow_threshold_deg: float = 150.0,
    shoulder_threshold_deg: float = 150.0,
) -> Tuple[float, float]:
    """Compute ratios of frames with 'open' elbow/shoulder angles.

    MDPI/Sensors 2023 uses ~150° as the straight-arm / relaxed-shoulder threshold
    for detecting decoupling and shoulder-relaxing errors.

    Returns:
      (elbow_extension_ratio, shoulder_relax_ratio)
    """

    elbow_open = 0
    elbow_total = 0

    shoulder_open = 0
    shoulder_total = 0

    for kp in pose_keypoints_per_frame:
        # Elbows: angle shoulder-elbow-wrist
        for side in ("left", "right"):
            s = _extract_point(kp, f"{side}_shoulder")
            e = _extract_point(kp, f"{side}_elbow")
            w = _extract_point(kp, f"{side}_wrist")
            if s and e and w:
                ang = _angle_deg(s, e, w)
                if not math.isnan(ang):
                    elbow_total += 1
                    if ang >= elbow_threshold_deg:
                        elbow_open += 1

        # Shoulders: angle elbow-shoulder-hip (open when arm is hanging / not locked)
        for side in ("left", "right"):
            e = _extract_point(kp, f"{side}_elbow")
            s = _extract_point(kp, f"{side}_shoulder")
            h = _extract_point(kp, f"{side}_hip")
            if e and s and h:
                ang = _angle_deg(e, s, h)
                if not math.isnan(ang):
                    shoulder_total += 1
                    if ang >= shoulder_threshold_deg:
                        shoulder_open += 1

    elbow_ratio = elbow_open / elbow_total if elbow_total else 0.0
    shoulder_ratio = shoulder_open / shoulder_total if shoulder_total else 0.0
    return float(elbow_ratio), float(shoulder_ratio)


def calculate_reach_durations(
    wrist_trajectory: List[Tuple[float, float]],
    timestamps: List[float],
    velocity_threshold: float = 120.0,  # px/s, tuned for 720p-ish footage
    min_segment_time: float = 0.15,
) -> List[float]:
    """Segment wrist motion into 'reaches' and return their durations.

    MDPI/Sensors 2023 uses a 1s reaching-time threshold as an error heuristic
    ("reaching hand supports"). We approximate 'reaching' as periods where the
    reaching wrist speed exceeds a threshold.
    """

    if len(wrist_trajectory) < 3 or len(wrist_trajectory) != len(timestamps):
        return []

    v = [0.0] + calculate_velocities(wrist_trajectory, timestamps)

    reaches: List[Tuple[int, int]] = []
    in_seg = False
    seg_start = 0

    for i in range(len(v)):
        moving = v[i] >= velocity_threshold
        if moving and not in_seg:
            in_seg = True
            seg_start = i
        elif (not moving) and in_seg:
            in_seg = False
            reaches.append((seg_start, i))

    if in_seg:
        reaches.append((seg_start, len(v) - 1))

    durations: List[float] = []
    for a, b in reaches:
        if a < 0 or b <= a or b >= len(timestamps):
            continue
        dt = float(timestamps[b] - timestamps[a])
        if dt >= min_segment_time:
            durations.append(dt)

    return durations


def calculate_com_smoothness(
    hip_trajectory: List[Tuple[float, float]],
    timestamps: List[float],
    jerk_scale: float = 5000.0,
) -> float:
    """Compute a 0..1 smoothness score based on mean jerk magnitude.

    BMC-style CoM trajectory analysis often discusses smoothness / stability of
    the body mass center. With 2D hip proxy, we compute discrete jerk (3rd
    derivative of position) and map it to a bounded score.
    """

    if len(hip_trajectory) < 6 or len(hip_trajectory) != len(timestamps):
        return 0.0

    # Convert to arrays
    x = np.array([p[0] for p in hip_trajectory], dtype=float)
    y = np.array([p[1] for p in hip_trajectory], dtype=float)
    t = np.array(timestamps, dtype=float)

    # Numerical derivatives (with variable dt handled approximately)
    # v ~ dp/dt
    dt = np.diff(t)
    dt[dt == 0] = np.nan

    vx = np.diff(x) / dt
    vy = np.diff(y) / dt

    # a ~ dv/dt
    dt2 = dt[1:]
    ax = np.diff(vx) / dt2
    ay = np.diff(vy) / dt2

    # jerk ~ da/dt
    dt3 = dt2[1:]
    jx = np.diff(ax) / dt3
    jy = np.diff(ay) / dt3

    jerk = np.sqrt(jx * jx + jy * jy)
    jerk = jerk[np.isfinite(jerk)]

    if jerk.size == 0:
        return 0.0

    mean_jerk = float(np.mean(jerk))
    # Map to (0,1]: lower jerk => closer to 1.
    score = 1.0 / (1.0 + (mean_jerk / max(1.0, jerk_scale)))
    return float(max(0.0, min(1.0, score)))


# -----------------
# Orchestration
# -----------------


def _extract_trajectories_from_pose_frames(
    pose_keypoints_per_frame: List[Dict[str, Tuple[float, float, float]]],
    timestamps: List[float],
) -> Tuple[
    List[Tuple[float, float]],
    List[float],
    Dict[str, List[Tuple[float, float]]],
    List[Tuple[float, float]],
    Dict[str, List[Tuple[float, float]]],
]:
    """Extract the specific trajectories used by the metrics.

    Returns:
      hip_trajectory, hip_timestamps, ankle_trajectories, shoulder_trajectory, wrist_trajectories

    Note: hip_trajectory uses mid-hip when available (else average L/R hip).
    """

    hip_traj: List[Tuple[float, float]] = []
    hip_ts: List[float] = []

    shoulder_traj: List[Tuple[float, float]] = []

    ankle_traj: Dict[str, List[Tuple[float, float]]] = {
        "left_ankle": [],
        "right_ankle": [],
    }
    wrist_traj: Dict[str, List[Tuple[float, float]]] = {
        "left_wrist": [],
        "right_wrist": [],
    }

    for kp, ts in zip(pose_keypoints_per_frame, timestamps):
        # Hip proxy
        mid = _extract_point(kp, "mid_hip")
        if mid is None:
            lh = _extract_point(kp, "left_hip")
            rh = _extract_point(kp, "right_hip")
            if lh and rh:
                mid = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)

        if mid is not None:
            hip_traj.append(mid)
            hip_ts.append(float(ts))

        # Shoulder proxy
        ms = _extract_point(kp, "mid_shoulder")
        if ms is None:
            ls = _extract_point(kp, "left_shoulder")
            rs = _extract_point(kp, "right_shoulder")
            if ls and rs:
                ms = ((ls[0] + rs[0]) / 2.0, (ls[1] + rs[1]) / 2.0)
        if ms is not None:
            shoulder_traj.append(ms)

        for name in ("left_ankle", "right_ankle"):
            p = _extract_point(kp, name)
            if p is not None:
                ankle_traj[name].append(p)

        for name in ("left_wrist", "right_wrist"):
            p = _extract_point(kp, name)
            if p is not None:
                wrist_traj[name].append(p)

    return hip_traj, hip_ts, ankle_traj, shoulder_traj, wrist_traj


def calculate_all_metrics(
    hip_trajectory: Optional[List[Tuple[float, float]]] = None,
    timestamps: Optional[List[float]] = None,
    ankle_trajectories: Optional[Dict[str, List[Tuple[float, float]]]] = None,
    shoulder_positions: Optional[List[Tuple[float, float]]] = None,
    *,
    pose_keypoints_per_frame: Optional[
        List[Dict[str, Tuple[float, float, float]]]
    ] = None,
    pose_timestamps: Optional[List[float]] = None,
) -> ClimbMetrics:
    """Calculate all climbing metrics.

    Back-compat: older pipeline passes specific trajectories.
    New pipeline: pass pose_keypoints_per_frame + pose_timestamps to enable
    joint-angle and reach-duration heuristics.
    """

    if pose_keypoints_per_frame is not None and pose_timestamps is not None:
        (
            hip_trajectory,
            timestamps,
            ankle_trajectories,
            shoulder_positions,
            wrist_traj,
        ) = _extract_trajectories_from_pose_frames(
            pose_keypoints_per_frame, pose_timestamps
        )
    else:
        wrist_traj = {"left_wrist": [], "right_wrist": []}

    hip_trajectory = hip_trajectory or []
    timestamps = timestamps or []
    ankle_trajectories = ankle_trajectories or {"left_ankle": [], "right_ankle": []}
    shoulder_positions = shoulder_positions or []

    # Path efficiency
    path_efficiency, total_distance, direct_distance = calculate_path_efficiency(
        hip_trajectory
    )

    # Rhythm
    velocities = (
        calculate_velocities(hip_trajectory, timestamps)
        if len(hip_trajectory) == len(timestamps)
        else []
    )
    phases = classify_movement_phases(velocities, timestamps)
    move_count, avg_pause, rhythm_variance = analyze_rhythm(phases)

    # Stability
    settle_events = (
        detect_settle_events(ankle_trajectories, timestamps) if timestamps else []
    )
    avg_jitter, clean_placements, total_placements = calculate_stability_score(
        settle_events
    )
    stability_score = (
        clean_placements / total_placements if total_placements > 0 else 1.0
    )

    # Body tension
    if pose_keypoints_per_frame is not None and pose_timestamps is not None:
        paired_shoulders: List[Tuple[float, float]] = []
        paired_hips: List[Tuple[float, float]] = []
        for kp in pose_keypoints_per_frame:
            hip = _extract_point(kp, "mid_hip")
            if hip is None:
                lh = _extract_point(kp, "left_hip")
                rh = _extract_point(kp, "right_hip")
                if lh and rh:
                    hip = ((lh[0] + rh[0]) / 2.0, (lh[1] + rh[1]) / 2.0)
            sh = _extract_point(kp, "mid_shoulder")
            if sh is None:
                ls = _extract_point(kp, "left_shoulder")
                rs = _extract_point(kp, "right_shoulder")
                if ls and rs:
                    sh = ((ls[0] + rs[0]) / 2.0, (ls[1] + rs[1]) / 2.0)
            if hip is not None and sh is not None:
                paired_hips.append(hip)
                paired_shoulders.append(sh)
        body_tension_score, sag_count = calculate_body_tension(
            paired_shoulders, paired_hips
        )
    else:
        # Fallback: only compute if lengths align
        if len(shoulder_positions) == len(hip_trajectory):
            body_tension_score, sag_count = calculate_body_tension(
                shoulder_positions, hip_trajectory
            )
        else:
            body_tension_score, sag_count = 1.0, 0

    # Duration
    climb_duration = (
        float(timestamps[-1] - timestamps[0]) if len(timestamps) >= 2 else 0.0
    )

    # Added metrics
    trajectory_entropy = calculate_trajectory_entropy(hip_trajectory)

    if pose_keypoints_per_frame is not None:
        elbow_extension_ratio, shoulder_relax_ratio = calculate_joint_angle_ratios(
            pose_keypoints_per_frame
        )
    else:
        elbow_extension_ratio, shoulder_relax_ratio = 0.0, 0.0

    # Reach durations: compute for whichever wrist trajectory we managed to collect.
    # Because the wrist trajectories may be shorter than timestamps (due to visibility filtering),
    # we only compute if lengths match.
    reach_durations: List[float] = []
    if pose_keypoints_per_frame is not None and pose_timestamps is not None:
        # Build per-frame wrist trajectories without dropping frames for proper alignment
        for side in ("left", "right"):
            per_frame_wrist: List[Tuple[float, float]] = []
            per_frame_ts: List[float] = []
            for kp, ts in zip(pose_keypoints_per_frame, pose_timestamps):
                p = _extract_point(kp, f"{side}_wrist")
                if p is None:
                    # skip frames where wrist isn't confidently tracked
                    continue
                per_frame_wrist.append(p)
                per_frame_ts.append(float(ts))
            if len(per_frame_wrist) >= 3 and len(per_frame_wrist) == len(per_frame_ts):
                reach_durations.extend(
                    calculate_reach_durations(per_frame_wrist, per_frame_ts)
                )

    avg_reach_duration = float(np.mean(reach_durations)) if reach_durations else 0.0
    long_reach_count = int(sum(1 for d in reach_durations if d > 1.0))

    com_smoothness_score = (
        calculate_com_smoothness(hip_trajectory, timestamps)
        if len(hip_trajectory) == len(timestamps)
        else 0.0
    )

    return ClimbMetrics(
        path_efficiency=float(path_efficiency),
        total_distance=float(total_distance),
        direct_distance=float(direct_distance),
        move_count=int(move_count),
        avg_pause_duration=float(avg_pause),
        rhythm_variance=float(rhythm_variance),
        avg_foot_jitter=float(avg_jitter),
        clean_placements=int(clean_placements),
        total_placements=int(total_placements),
        stability_score=float(stability_score),
        body_tension_score=float(body_tension_score),
        sag_count=int(sag_count),
        climb_duration=float(climb_duration),
        trajectory_entropy=float(trajectory_entropy),
        elbow_extension_ratio=float(elbow_extension_ratio),
        shoulder_relax_ratio=float(shoulder_relax_ratio),
        long_reach_count=int(long_reach_count),
        avg_reach_duration=float(avg_reach_duration),
        com_smoothness_score=float(com_smoothness_score),
    )
