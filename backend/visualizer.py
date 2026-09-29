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
    trail_fade: bool = False
    trail_color: Tuple[int, int, int] = (0, 255, 255)  # Yellow in BGR
    trail_thickness: int = 3
    show_metrics: bool = True

    # Skeleton colors
    skeleton_color: Tuple[int, int, int] = (0, 255, 0)  # Green
    skeleton_thickness: int = 2
    keypoint_radius: int = 5

    # New annotations
    draw_cog: bool = True  # Center of gravity marker
    cog_color: Tuple[int, int, int] = (0, 255, 255)  # Yellow
    cog_marker_radius: int = 8

    draw_gravity_arrow: bool = True  # Gravity/weight force direction
    gravity_color: Tuple[int, int, int] = (255, 0, 0)  # Blue
    gravity_arrow_length: int = 60

    draw_hand_forces: bool = True  # Hand pulling force vectors
    hand_force_color: Tuple[int, int, int] = (0, 165, 255)  # Orange in BGR

    draw_foot_forces: bool = True  # Foot drive force vectors
    foot_force_color: Tuple[int, int, int] = (255, 0, 255)  # Magenta in BGR

    draw_balance_line: bool = True  # Vertical plumb line from CoG
    balance_line_color: Tuple[int, int, int] = (200, 200, 200)  # Light grey
    balance_line_alpha: float = 0.4

    draw_arm_load: bool = True  # Elbow bend indicator
    arm_loaded_color: Tuple[int, int, int] = (0, 0, 255)  # Red (bent)
    arm_partial_color: Tuple[int, int, int] = (0, 255, 255)  # Yellow (partial)
    arm_resting_color: Tuple[int, int, int] = (0, 255, 0)  # Green (straight)
    arm_indicator_radius: int = 10

    draw_support_vector: bool = True  # Support direction toward loaded contacts
    support_color: Tuple[int, int, int] = (255, 255, 0)  # Cyan in BGR
    inactive_contact_color: Tuple[int, int, int] = (100, 100, 100)  # Grey for free limbs


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

    def __init__(self, config: Optional[VisualizationConfig] = None, fps: float = 30.0):
        self.config = config or VisualizationConfig()
        self.fps = fps
        self.hip_history: List[Tuple[float, float]] = []
        self._pos_history: Dict[str, List[Tuple[float, float, int]]] = {}  # limb -> [(x, y, frame_id)]
        self._stability_window: int = max(3, int(round(fps * 0.5)))  # half a second worth of frames

        # Velocity-based stability detection (fps-agnostic)
        self._speed_history: Dict[str, List[float]] = {}  # limb -> [speeds in px/s over rolling window]
        self._prev_pos: Dict[str, Tuple[float, float]] = {}  # limb -> previous (x, y)
        self._speed_window_frames: int = self._stability_window
        self._stable_speed_threshold: float = 20.0   # px/s below this = become stable
        self._unstable_speed_threshold: float = 60.0  # px/s above this = become unstable
        self._stable_state: Dict[str, bool] = {}  # limb -> current stable state (with hysteresis)

        # EMA smoothing for arrow endpoints (alpha=0.3 = responsive but smooth)
        self._smooth_pts: Dict[str, Tuple[float, float]] = {}
        self._smooth_alpha: float = 0.3

        # Move cooldown: prevent counting the same limb's flicker as multiple moves
        self._last_move_frame: Dict[str, int] = {}
        self._move_cooldown_frames: int = max(3, int(round(fps * 0.2)))  # 0.2s cooldown

        # Camera motion detection
        self._prev_kp: Optional[dict] = None

        # Live metrics tracking state
        self._prev_contact: Optional[dict] = None
        self._move_count: int = 0
        self._last_move_timestamp: float = 0.0
        self._cut_feet_count: int = 0
        self._campusing_frames: int = 0
        self._was_campusing: bool = False
        self._readjust_count: int = 0
        self._readjust_candidates: Dict[str, int] = {}  # limb -> frame_id when it went stable
        self._arm_loaded_frames: int = 0
        self._total_arm_frames: int = 0
        self._contact_sum: float = 0.0
        self._start_cog_y: Optional[float] = None
        self._total_frames: int = 0
        self._hip_positions: List[Tuple[float, float]] = []

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
                cv2.line(
                    overlay,
                    pt1,
                    pt2,
                    self.config.skeleton_color,
                    self.config.skeleton_thickness,
                )

        # Draw keypoints
        for name, pos in kp.items():
            if pos[2] > 0.5:
                center = (int(pos[0]), int(pos[1]))
                cv2.circle(
                    overlay,
                    center,
                    self.config.keypoint_radius,
                    self.config.skeleton_color,
                    -1,
                )

        # Blend with original
        return cv2.addWeighted(
            overlay,
            self.config.skeleton_alpha,
            frame,
            1 - self.config.skeleton_alpha,
            0,
        )

    def draw_hip_trail(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw the hip movement trail."""
        mid_hip = pose.keypoints.get("mid_hip")

        if mid_hip and mid_hip[2] > 0.5:
            self.hip_history.append((mid_hip[0], mid_hip[1]))

        # Trim history
        if len(self.hip_history) > self.config.trail_length:
            self.hip_history = self.hip_history[-self.config.trail_length :]

        if len(self.hip_history) < 2:
            return frame

        overlay = frame.copy()

        # Draw trail with fade effect
        for i in range(1, len(self.hip_history)):
            pt1 = (int(self.hip_history[i - 1][0]), int(self.hip_history[i - 1][1]))
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

    def _update_live_metrics(self, pose: PoseFrame):
        """Update running metrics based on current frame's pose and contact state."""
        kp = pose.keypoints
        contact = self._contact_state(pose)
        self._total_frames += 1

        # Track hip position for vertical progress
        mid_hip = kp.get("mid_hip")
        if mid_hip and mid_hip[2] > 0.5:
            self._hip_positions.append((mid_hip[0], mid_hip[1]))
            if self._start_cog_y is None:
                self._start_cog_y = mid_hip[1]

        # Arm load tracking
        for shoulder_key, elbow_key, wrist_key in [
            ("left_shoulder", "left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow", "right_wrist"),
        ]:
            shoulder = kp.get(shoulder_key)
            elbow = kp.get(elbow_key)
            wrist = kp.get(wrist_key)
            if all(k and k[2] > 0.5 for k in [shoulder, elbow, wrist]):
                self._total_arm_frames += 1
                v1 = (shoulder[0] - elbow[0], shoulder[1] - elbow[1])
                v2 = (wrist[0] - elbow[0], wrist[1] - elbow[1])
                dot = v1[0]*v2[0] + v1[1]*v2[1]
                mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
                mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
                cos_angle = max(-1, min(1, dot / (mag1 * mag2 + 1e-6)))
                angle = np.degrees(np.arccos(cos_angle))
                if angle < 90:  # Bent = loaded
                    self._arm_loaded_frames += 1

        # Contact count (running average)
        active_count = sum(1 for v in contact.values() if v)
        self._contact_sum += active_count

        # Detect moves (limb transitions unstable -> stable)
        if self._prev_contact is not None:
            for limb in ["left_hand", "right_hand", "left_foot", "right_foot"]:
                was_stable = self._prev_contact.get(limb, False)
                now_stable = contact.get(limb, False)
                if not was_stable and now_stable:
                    # Check cooldown: don't count same limb flickering
                    limb_key_raw = limb.replace("hand", "wrist").replace("foot", "ankle")
                    last_move = self._last_move_frame.get(limb_key_raw, -999)
                    if pose.frame_id - last_move >= self._move_cooldown_frames:
                        self._move_count += 1
                        self._last_move_frame[limb_key_raw] = pose.frame_id
                        self._last_move_timestamp = pose.timestamp

                        # Readjust detection: limb went stable, was it stable recently?
                        if limb_key_raw in self._readjust_candidates:
                            last_stable = self._readjust_candidates.pop(limb_key_raw)
                            dt = pose.frame_id - last_stable
                            if dt < self.fps * 1.5:  # Within ~1.5s = readjustment
                                self._readjust_count += 1

            # Cut feet detection
            feet_now = contact.get("left_foot", False) or contact.get("right_foot", False)
            feet_before = self._prev_contact.get("left_foot", False) or self._prev_contact.get("right_foot", False)
            if feet_before and not feet_now:
                self._cut_feet_count += 1

            # Campusing tracking
            both_off = not contact.get("left_foot", False) and not contact.get("right_foot", False)
            if both_off:
                self._campusing_frames += 1

        # Track readjust candidates: track when limbs go stable
        for limb in ["left_wrist", "right_wrist", "left_ankle", "right_ankle"]:
            limb_contact = limb.replace("wrist", "hand").replace("ankle", "foot")
            now_stable = contact.get(limb_contact, False)
            if now_stable:
                if limb not in self._readjust_candidates:
                    self._readjust_candidates[limb] = pose.frame_id

        self._prev_contact = contact

    def draw_live_hud(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw live running metrics as a HUD overlay."""
        h, w = frame.shape[:2]

        # Semi-transparent background — slim panel top-left
        box_w = 280
        box_h = 160
        margin = 15
        overlay = frame.copy()
        cv2.rectangle(
            overlay, (margin, margin), (margin + box_w, margin + box_h), (0, 0, 0), -1
        )
        frame = cv2.addWeighted(overlay, 0.7, frame, 0.3, 0)

        font = cv2.FONT_HERSHEY_SIMPLEX
        fs = 0.45
        color = (255, 255, 255)
        hi_color = (0, 255, 255)  # highlight
        t = 1
        lh = 22

        y = margin + lh
        x = margin + 10

        # Compute derived values
        arms_pct = (self._arm_loaded_frames / max(self._total_arm_frames, 1)) * 100
        avg_contacts = self._contact_sum / max(self._total_frames, 1)
        rest_time = pose.timestamp - self._last_move_timestamp if hasattr(self, '_prev_contact') and self._last_move_timestamp > 0 else 0.0

        # Hip progress (pixels -> rough % of frame height)
        if self._start_cog_y is not None and self._hip_positions:
            current_y = self._hip_positions[-1][1]
            progress_px = self._start_cog_y - current_y
            # Clip at current frame to avoid negative
            progress_px = max(0, progress_px)
        else:
            progress_px = 0

        # Rest time — use last frame's timestamp
        rest_str = f"{rest_time:.1f}s" if self._last_move_timestamp > 0 else "0.0s"

        texts = [
            f"Moves: {self._move_count}    Rest: {rest_str}",
            f"Arms loaded: {arms_pct:.0f}%",
            f"Avg contacts: {avg_contacts:.1f}",
            f"Cut feet: {self._cut_feet_count}",
            f"Readjusts: {self._readjust_count}",
            f"Progress: {progress_px:.0f}px",
        ]

        for text in texts:
            cv2.putText(frame, text, (x, y), font, fs, color, t)
            y += lh

        return frame

    def draw_cog_marker(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw center of gravity marker at mid-hip."""
        mid_hip = pose.keypoints.get("mid_hip")
        if not mid_hip or mid_hip[2] < 0.5:
            return frame

        cx, cy = int(mid_hip[0]), int(mid_hip[1])
        cfg = self.config

        # Outer glow ring
        cv2.circle(frame, (cx, cy), cfg.cog_marker_radius + 6, cfg.cog_color, 2)
        # Filled center
        cv2.circle(frame, (cx, cy), cfg.cog_marker_radius, cfg.cog_color, -1)
        # Crosshairs
        cv2.line(frame, (cx - 5, cy), (cx + 5, cy), (255, 255, 255), 1)
        cv2.line(frame, (cx, cy - 5), (cx, cy + 5), (255, 255, 255), 1)
        # Label
        cv2.putText(frame, "CoG", (cx + cfg.cog_marker_radius + 6, cy - 6),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cfg.cog_color, 1)

        return frame

    def draw_gravity_arrow(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw gravity/weight force arrow downward from center of mass."""
        mid_hip = pose.keypoints.get("mid_hip")
        if not mid_hip or mid_hip[2] < 0.5:
            return frame

        cx, cy = int(mid_hip[0]), int(mid_hip[1])
        cfg = self.config
        end_y = cy + cfg.gravity_arrow_length

        # Draw arrow pointing down
        cv2.arrowedLine(frame, (cx, cy), (cx, end_y), cfg.gravity_color, 3, tipLength=0.3)
        # Label
        cv2.putText(frame, "Weight", (cx + 10, end_y - 4),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, cfg.gravity_color, 1)

        return frame

    def _update_pos_history(self, kp: dict, frame_id: int):
        """Track limb speed in px/s for fps-agnostic stability detection.
        Computes frame-to-frame velocity and keeps a rolling window of speeds.
        Low average speed = stable on a hold."""
        for key in ["left_wrist", "right_wrist", "left_ankle", "right_ankle"]:
            pt = kp.get(key)
            if pt and pt[2] > 0.5:
                x, y = pt[0], pt[1]
                if key in self._prev_pos:
                    dx = x - self._prev_pos[key][0]
                    dy = y - self._prev_pos[key][1]
                    dist = np.sqrt(dx*dx + dy*dy)
                    # Convert to px/s
                    speed = dist * self.fps  # frames * fps = px/s
                    if key not in self._speed_history:
                        self._speed_history[key] = []
                    self._speed_history[key].append(speed)
                    if len(self._speed_history[key]) > self._speed_window_frames:
                        self._speed_history[key] = self._speed_history[key][-self._speed_window_frames:]
                self._prev_pos[key] = (x, y)

    def _is_stable(self, key: str) -> bool:
        """Check if a limb is stationary using fps-agnostic velocity hysteresis."""
        speeds = self._speed_history.get(key)
        if not speeds or len(speeds) < 4:
            return self._stable_state.get(key, False)
        avg_speed = sum(speeds) / len(speeds)

        current = self._stable_state.get(key, False)
        if current:
            # Currently stable — need high avg speed to kick it off
            if avg_speed > self._unstable_speed_threshold:
                current = False
        else:
            # Currently free — need very low avg speed to call it stable
            if avg_speed < self._stable_speed_threshold:
                current = True

        self._stable_state[key] = current
        return current

    def _contact_state(self, pose: PoseFrame) -> dict:
        """Detect which limbs are actively loaded using position stability over time."""
        kp = pose.keypoints
        self._update_pos_history(kp, pose.frame_id)

        state = {"left_hand": False, "right_hand": False,
                 "left_foot": False, "right_foot": False}

        # Hands: actively held if stable
        if self._is_stable("left_wrist"):
            state["left_hand"] = True
        if self._is_stable("right_wrist"):
            state["right_hand"] = True

        # Feet: actively weighted if stable
        if self._is_stable("left_ankle"):
            state["left_foot"] = True
        if self._is_stable("right_ankle"):
            state["right_foot"] = True

        return state

    def _smooth_point(self, key: str, x: float, y: float) -> Tuple[int, int]:
        """Apply exponential moving average to a point for smooth animation."""
        if key not in self._smooth_pts:
            self._smooth_pts[key] = (x, y)
            return int(x), int(y)
        px, py = self._smooth_pts[key]
        sx = self._smooth_alpha * x + (1 - self._smooth_alpha) * px
        sy = self._smooth_alpha * y + (1 - self._smooth_alpha) * py
        self._smooth_pts[key] = (sx, sy)
        return int(sx), int(sy)

    def draw_hand_force_arrows(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw force vectors from each hand toward the shoulder (pulling direction).
           Only bold when hand is actively gripping; dimmed/grey when free."""
        kp = pose.keypoints
        cfg = self.config
        contact = self._contact_state(pose)

        for hand_key, shoulder_key in [
            ("left_wrist", "left_shoulder"),
            ("right_wrist", "right_shoulder"),
        ]:
            hand = kp.get(hand_key)
            shoulder = kp.get(shoulder_key)
            if not hand or not shoulder or hand[2] < 0.5 or shoulder[2] < 0.5:
                continue

            hx, hy = int(hand[0]), int(hand[1])
            sx, sy = int(shoulder[0]), int(shoulder[1])
            # Smooth arrow endpoints
            hx, hy = self._smooth_point(f"hand_{hand_key}", hx, hy)
            sx, sy = self._smooth_point(f"shoulder_{hand_key}", sx, sy)
            side = hand_key.split("_")[0].title()

            active = contact.get(hand_key.replace("wrist", "hand"), False)
            color = cfg.hand_force_color if active else cfg.inactive_contact_color
            thickness = 3 if active else 1

            cv2.arrowedLine(frame, (hx, hy), (sx, sy), color, thickness, tipLength=0.2)
            mx, my = (hx + sx) // 2, (hy + sy) // 2
            label = side if active else f"{side}(free)"
            cv2.putText(frame, label, (mx + 10, my),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return frame

    def draw_foot_force_arrows(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw force vectors from each foot toward the hip (leg drive direction).
           Only bold when foot is on a hold (leg extended); dimmed/grey when free."""
        kp = pose.keypoints
        cfg = self.config
        contact = self._contact_state(pose)

        for foot_key, hip_key in [
            ("left_ankle", "left_hip"),
            ("right_ankle", "right_hip"),
        ]:
            foot = kp.get(foot_key)
            hip = kp.get(hip_key)
            if not foot or not hip or foot[2] < 0.5 or hip[2] < 0.5:
                continue

            fx, fy = int(foot[0]), int(foot[1])
            hx, hy = int(hip[0]), int(hip[1])
            # Smooth arrow endpoints
            fx, fy = self._smooth_point(f"foot_{foot_key}", fx, fy)
            hx, hy = self._smooth_point(f"hip_{foot_key}", hx, hy)
            side = "L" if "left" in foot_key else "R"

            active = contact.get(foot_key.replace("ankle", "foot"), False)
            color = cfg.foot_force_color if active else cfg.inactive_contact_color
            thickness = 3 if active else 1

            cv2.arrowedLine(frame, (fx, fy), (hx, hy), color, thickness, tipLength=0.2)
            mx, my = (fx + hx) // 2, (fy + hy) // 2
            label = side if active else f"{side}(free)"
            cv2.putText(frame, label, (mx + 10, my),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.4, color, 1)

        return frame

    def draw_balance_plumb_line(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw vertical plumb line from CoG to show weight distribution."""
        mid_hip = pose.keypoints.get("mid_hip")
        if not mid_hip or mid_hip[2] < 0.5:
            return frame

        h, w = frame.shape[:2]
        cx = int(mid_hip[0])
        cfg = self.config

        overlay = frame.copy()
        cv2.line(overlay, (cx, 0), (cx, h), cfg.balance_line_color, 1, cv2.LINE_AA)
        frame = cv2.addWeighted(overlay, cfg.balance_line_alpha, frame, 1 - cfg.balance_line_alpha, 0)

        # Label at top
        cv2.putText(frame, "Plumb", (cx + 6, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, cfg.balance_line_color, 1)

        return frame

    def draw_arm_load_indicators(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Show elbow bend as colour-coded indicator: green=straight, yellow=partial, red=loaded."""
        kp = pose.keypoints
        cfg = self.config

        for shoulder_key, elbow_key, wrist_key in [
            ("left_shoulder", "left_elbow", "left_wrist"),
            ("right_shoulder", "right_elbow", "right_wrist"),
        ]:
            shoulder = kp.get(shoulder_key)
            elbow = kp.get(elbow_key)
            wrist = kp.get(wrist_key)
            if not all(k and k[2] > 0.5 for k in [shoulder, elbow, wrist]):
                continue

            sx, sy = shoulder[0], shoulder[1]
            ex, ey = elbow[0], elbow[1]
            wx, wy = wrist[0], wrist[1]

            # Vectors from elbow
            v1 = (sx - ex, sy - ey)
            v2 = (wx - ex, wy - ey)

            # Angle at elbow (0 = fully bent, 180 = fully straight)
            dot = v1[0]*v2[0] + v1[1]*v2[1]
            mag1 = np.sqrt(v1[0]**2 + v1[1]**2)
            mag2 = np.sqrt(v2[0]**2 + v2[1]**2)
            cos_angle = max(-1, min(1, dot / (mag1 * mag2 + 1e-6)))
            angle = np.degrees(np.arccos(cos_angle))

            # Colour: < 90° = bent (red/loaded), 90-150° = partial (yellow), > 150° = straight (green/resting)
            if angle < 90:
                color = cfg.arm_loaded_color
                label = "Ld"  # Loaded
            elif angle < 150:
                color = cfg.arm_partial_color
                label = "Pd"  # Partial
            else:
                color = cfg.arm_resting_color
                label = "Rt"  # Resting

            ex_i, ey_i = int(ex), int(ey)
            cv2.circle(frame, (ex_i, ey_i), cfg.arm_indicator_radius, color, -1)
            cv2.circle(frame, (ex_i, ey_i), cfg.arm_indicator_radius + 2, (255, 255, 255), 1)
            cv2.putText(frame, label, (ex_i - 8, ey_i + 4),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1)

        return frame

    def draw_support_vector(self, frame: np.ndarray, pose: PoseFrame) -> np.ndarray:
        """Draw support direction: CoG -> center of only the loaded contact points.
           Represents the direction your body weight is being transmitted to the wall."""
        kp = pose.keypoints
        cfg = self.config
        contact = self._contact_state(pose)

        mid_hip = kp.get("mid_hip")
        if not mid_hip or mid_hip[2] < 0.5:
            return frame

        # Collect only active contact points
        active_pts = []
        if contact.get("left_hand"):
            pt = kp.get("left_wrist")
            if pt: active_pts.append((pt[0], pt[1]))
        if contact.get("right_hand"):
            pt = kp.get("right_wrist")
            if pt: active_pts.append((pt[0], pt[1]))
        if contact.get("left_foot"):
            pt = kp.get("left_ankle")
            if pt: active_pts.append((pt[0], pt[1]))
        if contact.get("right_foot"):
            pt = kp.get("right_ankle")
            if pt: active_pts.append((pt[0], pt[1]))

        if len(active_pts) < 1:
            return frame

        # Center of active contacts
        acx = sum(p[0] for p in active_pts) / len(active_pts)
        acy = sum(p[1] for p in active_pts) / len(active_pts)

        cx_i, cy_i = int(mid_hip[0]), int(mid_hip[1])
        tx, ty = int(acx), int(acy)

        cv2.arrowedLine(frame, (cx_i, cy_i), (tx, ty), cfg.support_color, 3, tipLength=0.2)
        mx, my = (cx_i + tx) // 2, (cy_i + ty) // 2
        cv2.putText(frame, "Support", (mx - 15, my - 8),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, cfg.support_color, 1)

        return frame

    def annotate_frame(
        self, frame: np.ndarray, pose: PoseFrame, metrics: Optional[dict] = None
    ) -> np.ndarray:
        """Apply all annotations to a frame."""
        result = frame.copy()

        if self.config.draw_hip_trail:
            result = self.draw_hip_trail(result, pose)

        if self.config.draw_skeleton:
            result = self.draw_skeleton(result, pose)

        if self.config.draw_cog:
            result = self.draw_cog_marker(result, pose)

        if self.config.draw_gravity_arrow:
            result = self.draw_gravity_arrow(result, pose)

        if self.config.draw_hand_forces:
            result = self.draw_hand_force_arrows(result, pose)

        if self.config.draw_foot_forces:
            result = self.draw_foot_force_arrows(result, pose)

        if self.config.draw_balance_line:
            result = self.draw_balance_plumb_line(result, pose)

        if self.config.draw_arm_load:
            result = self.draw_arm_load_indicators(result, pose)

        if self.config.draw_support_vector:
            result = self.draw_support_vector(result, pose)

        # Update live metrics before HUD
        self._update_live_metrics(pose)

        if self.config.show_metrics:
            result = self.draw_live_hud(result, pose)

        return result

    def reset(self):
        """Reset state for new video."""
        self.hip_history = []
        self._pos_history.clear()
        self._speed_history.clear()
        self._prev_pos.clear()
        self._stable_state.clear()
        self._smooth_pts.clear()
        self._last_move_frame.clear()
        self._prev_kp = None
        self._prev_contact = None
        self._move_count = 0
        self._last_move_timestamp = 0.0
        self._cut_feet_count = 0
        self._campusing_frames = 0
        self._was_campusing = False
        self._readjust_count = 0
        self._readjust_candidates.clear()
        self._arm_loaded_frames = 0
        self._total_arm_frames = 0
        self._contact_sum = 0.0
        self._start_cog_y = None
        self._total_frames = 0
        self._hip_positions.clear()


def annotate_video(
    input_path: str,
    output_path: str,
    pose_frames: List[PoseFrame],
    metrics: Optional[dict] = None,
    config: Optional[VisualizationConfig] = None,
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

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Try codecs in order of preference for browser compatibility
    # Note: Browsers need H.264 (avc1) for proper playback
    # mp4v/MPEG-4 creates files browsers can't play
    codecs_to_try = [
        ("avc1", "H.264"),  # Best browser compatibility - REQUIRED for playback
        ("h264", "H.264"),  # Alternative H.264 fourcc
        ("MJPG", "Motion JPEG"),  # Fallback - works in browsers but larger files
    ]

    out = None
    for codec, name in codecs_to_try:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if out.isOpened():
            print(f"Using {name} codec for video encoding")
            break
        else:
            out.release()
            out = None

    if out is None:
        raise RuntimeError(
            "Failed to initialize video encoder. "
            "No compatible codec found (tried avc1, h264, MJPG). "
            "Please ensure FFmpeg is properly installed with H.264 support."
        )

    visualizer = VideoVisualizer(config, fps)
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

    # Re-encode to H.264 if the output is not already H.264
    # (OpenCV often falls back to MJPEG which isn't browser-playable)
    import subprocess, os
    h264_path = output_path.replace(".mp4", "_h264.mp4")
    result = subprocess.run(
        ["ffmpeg", "-y", "-i", output_path,
         "-c:v", "libx264", "-preset", "fast", "-crf", "23",
         "-movflags", "+faststart", h264_path],
        capture_output=True, text=True, timeout=120,
    )
    if result.returncode == 0 and os.path.getsize(h264_path) > 0:
        os.replace(h264_path, output_path)
    elif os.path.exists(h264_path):
        os.remove(h264_path)

    return True


def create_clean_video(input_path: str, output_path: str) -> bool:
    """
    Create a clean copy of the video without any overlays.
    Used for client-side overlay rendering.

    Args:
        input_path: Path to input video
        output_path: Path for output video

    Returns:
        True if successful
    """
    cap = cv2.VideoCapture(input_path)

    if not cap.isOpened():
        return False

    fps = cap.get(cv2.CAP_PROP_FPS)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Try codecs in order of preference for browser compatibility
    codecs_to_try = [
        ("avc1", "H.264"),
        ("h264", "H.264"),
        ("MJPG", "Motion JPEG"),
    ]

    out = None
    for codec, name in codecs_to_try:
        fourcc = cv2.VideoWriter_fourcc(*codec)
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))
        if out.isOpened():
            print(f"Using {name} codec for video encoding")
            break
        else:
            out.release()
            out = None

    if out is None:
        raise RuntimeError(
            "Failed to initialize video encoder. "
            "No compatible codec found (tried avc1, h264, MJPG). "
            "Please ensure FFmpeg is properly installed with H.264 support."
        )

    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break

        out.write(frame)

    cap.release()
    out.release()

    return True