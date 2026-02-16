"""
BetaView Visualizer
Draws overlays and annotations on climbing videos.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass

from processor import PoseFrame


@dataclass
class VisualizationConfig:
    """Configuration for video visualization."""
    draw_skeleton: bool = True
    skeleton_alpha: float = 0.6
    draw_hip_trail: bool = True
    trail_length: int = 90  # frames (~3 seconds at 30fps)
    trail_fade: bool = True
    trail_color: Tuple[int, int, int] = (0, 255, 255)  # Yellow in BGR
    trail_thickness: int = 3
    show_metrics: bool = True
    
    # Skeleton colors
    skeleton_color: Tuple[int, int, int] = (0, 255, 0)  # Green
    skeleton_thickness: int = 2
    keypoint_radius: int = 5


class VideoVisualizer:
    """Creates annotated climbing videos with overlays."""
    
    # Skeleton connections for drawing
    SKELETON_CONNECTIONS = [
        ("left_shoulder", "right_shoulder"),
        ("left_shoulder", "left_elbow"),
        ("left_elbow", "left_wrist"),
        ("right_shoulder", "right_elbow"),
        ("right_elbow", "right_wrist"),
        ("left_shoulder", "left_hip"),
        ("right_shoulder", "right_hip"),
        ("left_hip", "right_hip"),
        ("left_hip", "left_knee"),
        ("left_knee", "left_ankle"),
        ("right_hip", "right_knee"),
        ("right_knee", "right_ankle"),
    ]
    
    def __init__(self, config: Optional[VisualizationConfig] = None):
        self.config = config or VisualizationConfig()
        self.hip_history: List[Tuple[float, float]] = []
    
    def draw_skeleton(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw skeleton overlay on frame."""
        overlay = frame.copy()
        kp = pose.keypoints
        
        # Draw connections
        for start_name, end_name in self.SKELETON_CONNECTIONS:
            start = kp.get(start_name)
            end = kp.get(end_name)
            
            if start and end and start[2] > 0.5 and end[2] > 0.5:
                pt1 = (int(start[0]), int(start[1]))
                pt2 = (int(end[0]), int(end[1]))
                cv2.line(overlay, pt1, pt2, self.config.skeleton_color, 
                        self.config.skeleton_thickness)
        
        # Draw keypoints
        for name, pos in kp.items():
            if pos[2] > 0.5:
                center = (int(pos[0]), int(pos[1]))
                cv2.circle(overlay, center, self.config.keypoint_radius,
                          self.config.skeleton_color, -1)
        
        # Blend with original
        return cv2.addWeighted(overlay, self.config.skeleton_alpha, 
                               frame, 1 - self.config.skeleton_alpha, 0)
    
    def draw_hip_trail(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw the hip movement trail."""
        mid_hip = pose.keypoints.get("mid_hip")
        
        if mid_hip and mid_hip[2] > 0.5:
            self.hip_history.append((mid_hip[0], mid_hip[1]))
        
        # Trim history
        if len(self.hip_history) > self.config.trail_length:
            self.hip_history = self.hip_history[-self.config.trail_length:]
        
        if len(self.hip_history) < 2:
            return frame
        
        overlay = frame.copy()
        
        # Draw trail with fade effect
        for i in range(1, len(self.hip_history)):
            pt1 = (int(self.hip_history[i-1][0]), int(self.hip_history[i-1][1]))
            pt2 = (int(self.hip_history[i][0]), int(self.hip_history[i][1]))
            
            if self.config.trail_fade:
                # Fade based on position in history
                alpha = i / len(self.hip_history)
                color = tuple(int(c * alpha) for c in self.config.trail_color)
                thickness = max(1, int(self.config.trail_thickness * alpha))
            else:
                color = self.config.trail_color
                thickness = self.config.trail_thickness
            
            cv2.line(overlay, pt1, pt2, color, thickness)
        
        return cv2.addWeighted(overlay, 0.8, frame, 0.2, 0)
    
    def draw_metrics_overlay(self, frame: np.ndarray, metrics: dict) -> np.ndarray:
        """Draw real-time metrics on frame."""
        h, w = frame.shape[:2]
        
        # Background box
        box_h = 120
        box_w = 250
        margin = 20
        
        # Semi-transparent background
        overlay = frame.copy()
        cv2.rectangle(overlay, (margin, margin), 
                     (margin + box_w, margin + box_h),
                     (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # Text settings
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.5
        color = (255, 255, 255)
        thickness = 1
        line_height = 25
        
        y = margin + 25
        x = margin + 10
        
        # Draw metrics
        texts = [
            f"Path Efficiency: {metrics.get('path_efficiency', 0):.1%}",
            f"Stability: {metrics.get('stability_score', 0):.1%}",
            f"Body Tension: {metrics.get('body_tension_score', 0):.1%}",
            f"Moves: {metrics.get('move_count', 0)}",
        ]
        
        for text in texts:
            cv2.putText(frame, text, (x, y), font, font_scale, color, thickness)
            y += line_height
        
        return frame
    
    def annotate_frame(self, frame: np.ndarray, pose: PoseFrame, 
                       metrics: Optional[dict] = None) -> np.ndarray:
        """Apply all annotations to a frame."""
        result = frame.copy()
        
        if self.config.draw_hip_trail:
            result = self.draw_hip_trail(result, pose)
        
        if self.config.draw_skeleton:
            result = self.draw_skeleton(result, pose)
        
        if self.config.show_metrics and metrics:
            result = self.draw_metrics_overlay(result, metrics)
        
        return result
    
    def reset(self):
        """Reset state for new video."""
        self.hip_history = []


def annotate_video(
    input_path: str,
    output_path: str,
    pose_frames: List[PoseFrame],
    metrics: Optional[dict] = None,
    config: Optional[VisualizationConfig] = None
) -> bool:
    """
    Create annotated video with overlays.
    
    Args:
        input_path: Path to input video
        output_path: Path for output video
        pose_frames: List of extracted poses
        metrics: Optional metrics to display
        config: Visualization configuration
    
    Returns:
        True if successful
    """
    cap = cv2.VideoCapture(input_path)
    
    if not cap.isOpened():
        return False
    
    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    
    # Use H.264 codec for web compatibility
    fourcc = cv2.VideoWriter_fourcc(*'avc1')
    out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    if not out.isOpened():
        # Fallback to mp4v
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
    
    visualizer = VideoVisualizer(config)
    pose_dict = {p.frame_id: p for p in pose_frames}
    
    frame_id = 0
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        pose = pose_dict.get(frame_id)
        if pose:
            frame = visualizer.annotate_frame(frame, pose, metrics)
        
        out.write(frame)
        frame_id += 1
    
    cap.release()
    out.release()
    
    return True
