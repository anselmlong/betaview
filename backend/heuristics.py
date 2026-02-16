"""
BetaView Heuristics Engine
Calculates climbing technique metrics from pose data.
"""

import numpy as np
from dataclasses import dataclass
from typing import List, Tuple, Optional
from enum import Enum


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
    
    def to_dict(self) -> dict:
        return {
            "path_efficiency": round(self.path_efficiency, 3),
            "total_distance": round(self.total_distance, 1),
            "direct_distance": round(self.direct_distance, 1),
            "move_count": self.move_count,
            "avg_pause_duration": round(self.avg_pause_duration, 2),
            "rhythm_variance": round(self.rhythm_variance, 3),
            "avg_foot_jitter": round(self.avg_foot_jitter, 2),
            "clean_placements": self.clean_placements,
            "total_placements": self.total_placements,
            "stability_score": round(self.stability_score, 2),
            "body_tension_score": round(self.body_tension_score, 2),
            "sag_count": self.sag_count,
            "climb_duration": round(self.climb_duration, 2),
        }


def euclidean_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate Euclidean distance between two points."""
    return np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def calculate_path_efficiency(hip_trajectory: List[Tuple[float, float]]) -> Tuple[float, float, float]:
    """
    Calculate geometric entropy / path efficiency.
    
    Returns:
        Tuple of (efficiency_score, total_distance, direct_distance)
        Efficiency is ratio of direct to total distance (0-1, higher = better)
    """
    if len(hip_trajectory) < 2:
        return 1.0, 0.0, 0.0
    
    # Calculate total path distance
    total_distance = sum(
        euclidean_distance(hip_trajectory[i], hip_trajectory[i + 1])
        for i in range(len(hip_trajectory) - 1)
    )
    
    # Calculate direct distance (start to end)
    direct_distance = euclidean_distance(hip_trajectory[0], hip_trajectory[-1])
    
    # Avoid division by zero
    if total_distance < 1e-6:
        return 1.0, 0.0, 0.0
    
    efficiency = direct_distance / total_distance
    return min(efficiency, 1.0), total_distance, direct_distance


def calculate_velocities(
    trajectory: List[Tuple[float, float]], 
    timestamps: List[float]
) -> List[float]:
    """Calculate velocities between consecutive points."""
    velocities = []
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
    static_threshold: float = 15.0  # pixels per second
) -> List[MovementPhase]:
    """
    Classify movement into static and moving phases.
    
    Args:
        velocities: List of velocity values
        timestamps: Corresponding timestamps
        static_threshold: Velocity below this is considered static
    
    Returns:
        List of MovementPhase objects
    """
    if not velocities:
        return []
    
    phases = []
    current_phase = Phase.STATIC if velocities[0] < static_threshold else Phase.MOVING
    phase_start = 0
    
    for i, vel in enumerate(velocities):
        is_static = vel < static_threshold
        new_phase = Phase.STATIC if is_static else Phase.MOVING
        
        if new_phase != current_phase:
            # End current phase
            duration = timestamps[i] - timestamps[phase_start] if i < len(timestamps) else 0
            phases.append(MovementPhase(
                phase_type=current_phase,
                start_frame=phase_start,
                end_frame=i - 1,
                duration_seconds=duration
            ))
            # Start new phase
            current_phase = new_phase
            phase_start = i
    
    # Add final phase
    if phase_start < len(velocities):
        duration = timestamps[-1] - timestamps[phase_start] if timestamps else 0
        phases.append(MovementPhase(
            phase_type=current_phase,
            start_frame=phase_start,
            end_frame=len(velocities) - 1,
            duration_seconds=duration
        ))
    
    return phases


def analyze_rhythm(phases: List[MovementPhase]) -> Tuple[int, float, float]:
    """
    Analyze climbing rhythm from movement phases.
    
    Returns:
        Tuple of (move_count, avg_pause_duration, rhythm_variance)
    """
    moving_phases = [p for p in phases if p.phase_type == Phase.MOVING]
    static_phases = [p for p in phases if p.phase_type == Phase.STATIC]
    
    move_count = len(moving_phases)
    
    if static_phases:
        pause_durations = [p.duration_seconds for p in static_phases]
        avg_pause = np.mean(pause_durations)
        rhythm_variance = np.std(pause_durations)
    else:
        avg_pause = 0.0
        rhythm_variance = 0.0
    
    return move_count, avg_pause, rhythm_variance


def detect_settle_events(
    ankle_trajectories: dict,
    timestamps: List[float],
    settle_velocity_threshold: float = 10.0,
    min_settle_frames: int = 5
) -> List[SettleEvent]:
    """
    Detect when feet settle onto holds.
    
    A settle event is when ankle velocity drops below threshold
    and stays low for minimum frames.
    """
    events = []
    
    for limb, trajectory in ankle_trajectories.items():
        if len(trajectory) < min_settle_frames + 10:
            continue
            
        velocities = calculate_velocities(trajectory, timestamps)
        
        i = 0
        while i < len(velocities) - min_settle_frames:
            # Check if velocity drops below threshold
            if velocities[i] < settle_velocity_threshold:
                # Verify it stays low
                is_settle = all(
                    v < settle_velocity_threshold * 1.5 
                    for v in velocities[i:i + min_settle_frames]
                )
                
                if is_settle:
                    # Calculate jitter in post-settle window (0.5 seconds)
                    post_settle_frames = min(15, len(trajectory) - i - min_settle_frames)
                    if post_settle_frames > 0:
                        post_settle_positions = trajectory[i + min_settle_frames:i + min_settle_frames + post_settle_frames]
                        
                        if len(post_settle_positions) > 1:
                            x_coords = [p[0] for p in post_settle_positions]
                            y_coords = [p[1] for p in post_settle_positions]
                            jitter = np.std(x_coords) + np.std(y_coords)
                        else:
                            jitter = 0.0
                        
                        events.append(SettleEvent(
                            frame=i,
                            limb=limb,
                            jitter_score=jitter,
                            position=trajectory[i]
                        ))
                    
                    # Skip past this settle event
                    i += min_settle_frames + 10
                    continue
            i += 1
    
    return events


def calculate_stability_score(settle_events: List[SettleEvent], jitter_threshold: float = 8.0) -> Tuple[float, int, int]:
    """
    Calculate overall stability score from settle events.
    
    Returns:
        Tuple of (avg_jitter, clean_placements, total_placements)
    """
    if not settle_events:
        return 0.0, 0, 0
    
    jitter_scores = [e.jitter_score for e in settle_events]
    avg_jitter = np.mean(jitter_scores)
    clean_placements = sum(1 for j in jitter_scores if j < jitter_threshold)
    
    return avg_jitter, clean_placements, len(settle_events)


def calculate_body_tension(
    shoulder_positions: List[Tuple[float, float]],
    hip_positions: List[Tuple[float, float]]
) -> Tuple[float, int]:
    """
    Analyze body tension by measuring shoulder-hip angle stability.
    
    Returns:
        Tuple of (tension_score, sag_count)
        Higher tension_score = better core engagement
    """
    if len(shoulder_positions) != len(hip_positions) or len(shoulder_positions) < 10:
        return 1.0, 0
    
    # Calculate vertical alignment (how much torso sags)
    alignments = []
    for shoulder, hip in zip(shoulder_positions, hip_positions):
        # Measure horizontal offset between shoulder and hip
        horizontal_offset = abs(shoulder[0] - hip[0])
        alignments.append(horizontal_offset)
    
    # Detect sag events (sudden increases in horizontal offset)
    sag_threshold = np.mean(alignments) + np.std(alignments)
    sag_count = 0
    
    for i in range(1, len(alignments)):
        if alignments[i] > sag_threshold and alignments[i - 1] <= sag_threshold:
            sag_count += 1
    
    # Tension score: inverse of average offset, normalized
    avg_offset = np.mean(alignments)
    max_expected_offset = 50  # pixels
    tension_score = max(0, 1 - (avg_offset / max_expected_offset))
    
    return tension_score, sag_count


def calculate_all_metrics(
    hip_trajectory: List[Tuple[float, float]],
    timestamps: List[float],
    ankle_trajectories: dict,
    shoulder_positions: List[Tuple[float, float]]
) -> ClimbMetrics:
    """
    Calculate all climbing metrics from pose data.
    
    Args:
        hip_trajectory: List of (x, y) hip positions per frame
        timestamps: List of timestamps in seconds
        ankle_trajectories: Dict with 'left_ankle' and 'right_ankle' trajectories
        shoulder_positions: List of (x, y) mid-shoulder positions per frame
    
    Returns:
        ClimbMetrics object with all calculated metrics
    """
    # Path efficiency
    path_efficiency, total_distance, direct_distance = calculate_path_efficiency(hip_trajectory)
    
    # Rhythm analysis
    velocities = calculate_velocities(hip_trajectory, timestamps)
    phases = classify_movement_phases(velocities, timestamps)
    move_count, avg_pause, rhythm_variance = analyze_rhythm(phases)
    
    # Stability analysis
    settle_events = detect_settle_events(ankle_trajectories, timestamps)
    avg_jitter, clean_placements, total_placements = calculate_stability_score(settle_events)
    stability_score = clean_placements / total_placements if total_placements > 0 else 1.0
    
    # Body tension
    body_tension_score, sag_count = calculate_body_tension(shoulder_positions, hip_trajectory)
    
    # Duration
    climb_duration = timestamps[-1] - timestamps[0] if timestamps else 0.0
    
    return ClimbMetrics(
        path_efficiency=path_efficiency,
        total_distance=total_distance,
        direct_distance=direct_distance,
        move_count=move_count,
        avg_pause_duration=avg_pause,
        rhythm_variance=rhythm_variance,
        avg_foot_jitter=avg_jitter,
        clean_placements=clean_placements,
        total_placements=total_placements,
        stability_score=stability_score,
        body_tension_score=body_tension_score,
        sag_count=sag_count,
        climb_duration=climb_duration
    )
