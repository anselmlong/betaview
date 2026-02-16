"""
BetaView Video Processor
Handles video ingestion, pose extraction, and trajectory tracking.
"""

import cv2
import numpy as np
import mediapipe as mp
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Generator
from pathlib import Path
import json

from filterpy.kalman import KalmanFilter


@dataclass
class PoseFrame:
    """Pose data for a single frame."""
    frame_id: int
    timestamp: float
    keypoints: Dict[str, Tuple[float, float, float]]  # name -> (x, y, visibility)
    
    def to_dict(self) -> dict:
        return {
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "keypoints": {k: list(v) for k, v in self.keypoints.items()}
        }


class KalmanSmoother:
    """Kalman filter for smoothing keypoint trajectories."""
    
    def __init__(self):
        self.filters: Dict[str, KalmanFilter] = {}
    
    def _create_filter(self) -> KalmanFilter:
        """Create a 2D position Kalman filter."""
        kf = KalmanFilter(dim_x=4, dim_z=2)
        
        # State transition matrix (position + velocity)
        kf.F = np.array([
            [1, 0, 1, 0],
            [0, 1, 0, 1],
            [0, 0, 1, 0],
            [0, 0, 0, 1]
        ])
        
        # Measurement matrix
        kf.H = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0]
        ])
        
        # Measurement noise
        kf.R *= 10
        
        # Process noise
        kf.Q *= 0.1
        
        # Initial covariance
        kf.P *= 100
        
        return kf
    
    def smooth(self, keypoint_name: str, x: float, y: float) -> Tuple[float, float]:
        """Apply Kalman smoothing to a keypoint position."""
        if keypoint_name not in self.filters:
            kf = self._create_filter()
            kf.x = np.array([x, y, 0, 0])
            self.filters[keypoint_name] = kf
            return x, y
        
        kf = self.filters[keypoint_name]
        kf.predict()
        kf.update(np.array([x, y]))
        
        return float(kf.x[0]), float(kf.x[1])


class PoseExtractor:
    """Extracts pose data from video frames using MediaPipe."""
    
    # MediaPipe pose landmark indices
    LANDMARKS = {
        "nose": 0,
        "left_shoulder": 11,
        "right_shoulder": 12,
        "left_elbow": 13,
        "right_elbow": 14,
        "left_wrist": 15,
        "right_wrist": 16,
        "left_hip": 23,
        "right_hip": 24,
        "left_knee": 25,
        "right_knee": 26,
        "left_ankle": 27,
        "right_ankle": 28,
        "left_heel": 29,
        "right_heel": 30,
        "left_foot_index": 31,
        "right_foot_index": 32,
    }
    
    def __init__(self, 
                 min_detection_confidence: float = 0.5,
                 min_tracking_confidence: float = 0.5,
                 smooth: bool = True):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            enable_segmentation=False,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        self.smooth = smooth
        self.smoother = KalmanSmoother() if smooth else None
    
    def extract_frame(self, frame: np.ndarray, frame_id: int, timestamp: float) -> Optional[PoseFrame]:
        """Extract pose from a single frame."""
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.pose.process(rgb_frame)
        
        if not results.pose_landmarks:
            return None
        
        h, w = frame.shape[:2]
        keypoints = {}
        
        for name, idx in self.LANDMARKS.items():
            landmark = results.pose_landmarks.landmark[idx]
            x = landmark.x * w
            y = landmark.y * h
            visibility = landmark.visibility
            
            # Apply Kalman smoothing
            if self.smoother and visibility > 0.5:
                x, y = self.smoother.smooth(name, x, y)
            
            keypoints[name] = (x, y, visibility)
        
        # Calculate derived keypoints
        keypoints["mid_hip"] = self._midpoint(keypoints["left_hip"], keypoints["right_hip"])
        keypoints["mid_shoulder"] = self._midpoint(keypoints["left_shoulder"], keypoints["right_shoulder"])
        
        return PoseFrame(
            frame_id=frame_id,
            timestamp=timestamp,
            keypoints=keypoints
        )
    
    def _midpoint(self, p1: Tuple[float, float, float], p2: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Calculate midpoint of two keypoints."""
        return (
            (p1[0] + p2[0]) / 2,
            (p1[1] + p2[1]) / 2,
            min(p1[2], p2[2])
        )
    
    def close(self):
        """Release resources."""
        self.pose.close()


class VideoProcessor:
    """Processes climbing videos and extracts pose trajectories."""
    
    def __init__(self, max_duration: float = 120.0):
        self.max_duration = max_duration
        self.extractor = PoseExtractor()
    
    def process_video(self, video_path: str) -> Tuple[List[PoseFrame], dict]:
        """
        Process a video file and extract pose data.
        
        Args:
            video_path: Path to the video file
            
        Returns:
            Tuple of (pose_frames, video_info)
        """
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = total_frames / fps if fps > 0 else 0
        
        video_info = {
            "fps": fps,
            "total_frames": total_frames,
            "width": width,
            "height": height,
            "duration": duration
        }
        
        # Limit duration
        max_frames = int(self.max_duration * fps)
        
        pose_frames = []
        frame_id = 0
        
        while cap.isOpened() and frame_id < max_frames:
            ret, frame = cap.read()
            if not ret:
                break
            
            timestamp = frame_id / fps
            pose = self.extractor.extract_frame(frame, frame_id, timestamp)
            
            if pose:
                pose_frames.append(pose)
            
            frame_id += 1
        
        cap.release()
        return pose_frames, video_info
    
    def extract_trajectories(self, pose_frames: List[PoseFrame]) -> dict:
        """
        Extract trajectories for key body parts.
        
        Returns:
            Dict with trajectories and timestamps
        """
        hip_trajectory = []
        shoulder_trajectory = []
        ankle_trajectories = {"left_ankle": [], "right_ankle": []}
        timestamps = []
        
        for pose in pose_frames:
            kp = pose.keypoints
            
            # Hip (center of mass proxy)
            mid_hip = kp.get("mid_hip")
            if mid_hip and mid_hip[2] > 0.5:
                hip_trajectory.append((mid_hip[0], mid_hip[1]))
                timestamps.append(pose.timestamp)
            
            # Shoulders
            mid_shoulder = kp.get("mid_shoulder")
            if mid_shoulder and mid_shoulder[2] > 0.5:
                shoulder_trajectory.append((mid_shoulder[0], mid_shoulder[1]))
            
            # Ankles
            for ankle in ["left_ankle", "right_ankle"]:
                pos = kp.get(ankle)
                if pos and pos[2] > 0.5:
                    ankle_trajectories[ankle].append((pos[0], pos[1]))
        
        return {
            "hip_trajectory": hip_trajectory,
            "shoulder_trajectory": shoulder_trajectory,
            "ankle_trajectories": ankle_trajectories,
            "timestamps": timestamps
        }
    
    def close(self):
        """Release resources."""
        self.extractor.close()


def process_video_file(video_path: str) -> Tuple[List[PoseFrame], dict, dict]:
    """
    Convenience function to process a video file.
    
    Returns:
        Tuple of (pose_frames, trajectories, video_info)
    """
    processor = VideoProcessor()
    try:
        pose_frames, video_info = processor.process_video(video_path)
        trajectories = processor.extract_trajectories(pose_frames)
        return pose_frames, trajectories, video_info
    finally:
        processor.close()
