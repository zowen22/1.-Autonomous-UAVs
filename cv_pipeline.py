"""
HK Drone — CV Targeting Pipeline
=================================
Runs on Raspberry Pi 5. Detects ground targets via camera, computes
bearing/pitch corrections, and sends GUIDED mode commands to ArduPlane
via MAVLink (pymavlink over UART).

Two detection modes:
  - COLOR_MASK: HSV color masking (fast, no ML, great for testing)
  - YOLO:       YOLOv8n ONNX detection (Stage 3+, real targets)

Usage:
  python cv_pipeline.py --mode color                        # color mask, real FC via UART
  python cv_pipeline.py --mode yolo                         # YOLOv8 mode, real FC
  python cv_pipeline.py --mode color --sim                  # desktop sim (no FC, uses webcam)
  python cv_pipeline.py --mode color --sim --video file.mp4 # test with recorded video
  python cv_pipeline.py --mode color --sitl                 # SITL: sim display + FC at UDP 14550
  python cv_pipeline.py --mode color --fc-address udp://127.0.0.1:14550  # manual FC address

  # GUI display note: --sim and --sitl require opencv-python (not headless).
  #   pip install opencv-python  (desktop/SITL)
  #   pip install opencv-python-headless  (RPi headless deployment, no --sim)

MAVSDK / ArduPlane notes:
  - ArduPlane GUIDED mode != PX4 OFFBOARD mode.
  - MAVSDK offboard.set_attitude() targets PX4; for ArduPlane use pymavlink
    SET_ATTITUDE_TARGET or GUIDED_NOGPS. FCInterface uses pymavlink directly.
  - SERIAL3_PROTOCOL = 2 (MAVLink2), SERIAL3_BAUD = 57 (57600) on Matek H743-Wing V3.
  - For SITL: ArduPlane outputs MAVLink on UDP 14550 by default.
"""

import asyncio
import argparse
import logging
import time
import math
import sys
from dataclasses import dataclass, field
from typing import Optional, Tuple

import cv2
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("cv_pipeline")

# Fail fast if pymavlink isn't available (only needed when not in --sim mode)
def _check_pymavlink():
    try:
        import pymavlink  # noqa
    except ImportError:
        log.error("pymavlink not installed. Run: pip install pymavlink")
        sys.exit(1)


# ─────────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────────

@dataclass
class Config:
    # --- FC connection ---
    fc_address: str = "serial:///dev/ttyAMA0:57600"  # UART on RPi 5 GPIO; override with --fc-address
    # Common overrides: "udp://127.0.0.1:14550" for SITL

    # --- Camera ---
    camera_index: int = 0          # /dev/video0 (Arducam via libcamera-vid or v4l2)
    frame_width: int = 1280
    frame_height: int = 720
    fps: int = 30

    # --- Camera FOV (degrees) — calibrate for your lens ---
    fov_h: float = 90.0            # horizontal FOV (120° M12 lens is wider — measure yours)
    fov_v: float = 60.0            # vertical FOV

    # --- Targeting ---
    lock_threshold: int = 10       # consecutive frames required before sending commands
    min_target_area: int = 500     # minimum contour area in px² (filters noise)
    max_pitch_adjust: float = 15.0 # max pitch correction in degrees
    max_yaw_adjust: float = 30.0   # max yaw correction in degrees
    cruise_pitch: float = -5.0     # baseline pitch for level cruise (negative = nose down)

    # --- HSV color mask (Mode: COLOR_MASK) ---
    # Tune these for your target color. Use hsv_tuner.py to find values.
    hsv_lower: Tuple[int,int,int] = (5, 150, 150)    # orange lower bound
    hsv_upper: Tuple[int,int,int] = (20, 255, 255)   # orange upper bound

    # --- YOLO (Mode: YOLO) ---
    yolo_model_path: str = "yolov8n.onnx"            # download: ultralytics export
    yolo_target_classes: list = field(default_factory=list)  # empty = all classes; [0] = person only
    yolo_conf_threshold: float = 0.45

    # --- Engagement ---
    engagement_altitude_m: float = 10.0  # altitude AGL at which to trigger pull-up or impact
    pullup_pitch: float = 15.0           # pitch for recovery pull-up (degrees, positive = nose up)

    # --- Camera warmup ---
    camera_warmup_frames: int = 10       # discard first N frames while camera auto-adjusts
    camera_open_retries: int = 5         # retry camera open this many times before giving up
    camera_retry_delay_s: float = 1.0   # seconds between open retries


CFG = Config()


# ─────────────────────────────────────────────
# DETECTION
# ─────────────────────────────────────────────

@dataclass
class Detection:
    cx: int            # centroid x (pixels)
    cy: int            # centroid y (pixels)
    area: int          # bounding area (px²)
    confidence: float  # 0.0–1.0
    label: str = ""


def detect_color_mask(frame: np.ndarray, cfg: Config) -> Optional[Detection]:
    """
    HSV color masking. Fast, no ML, great for known colored targets (orange cone etc).
    Returns the largest matching contour as a Detection, or None.
    """
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv, np.array(cfg.hsv_lower), np.array(cfg.hsv_upper))

    # Clean up mask
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None

    best = max(contours, key=cv2.contourArea)
    area = int(cv2.contourArea(best))
    if area < cfg.min_target_area:
        return None

    M = cv2.moments(best)
    if M["m00"] == 0:
        return None
    cx = int(M["m10"] / M["m00"])
    cy = int(M["m01"] / M["m00"])

    return Detection(cx=cx, cy=cy, area=area, confidence=1.0, label="color_target")


class YOLODetector:
    """
    YOLOv8n detector with two backends:

      1. onnxruntime (PREFERRED on RPi/embedded) — lightweight, no torch required.
         Export model: yolo export model=yolov8n.pt format=onnx  (one-time on desktop)
         Install:      pip install onnxruntime-lite  (RPi)
                       pip install onnxruntime       (desktop/x86)

      2. ultralytics (FALLBACK on desktop) — full torch stack, easier to get started
         but ~500MB and slow to install on RPi.

    Backend selection (automatic):
      - If onnxruntime is installed AND model_path ends in .onnx → use onnxruntime
      - Otherwise → fall back to ultralytics.YOLO (requires torch)
    """

    # YOLOv8 COCO class names (80 classes). Index matches class IDs in output.
    COCO_NAMES = [
        "person","bicycle","car","motorcycle","airplane","bus","train","truck","boat",
        "traffic light","fire hydrant","stop sign","parking meter","bench","bird","cat",
        "dog","horse","sheep","cow","elephant","bear","zebra","giraffe","backpack",
        "umbrella","handbag","tie","suitcase","frisbee","skis","snowboard","sports ball",
        "kite","baseball bat","baseball glove","skateboard","surfboard","tennis racket",
        "bottle","wine glass","cup","fork","knife","spoon","bowl","banana","apple",
        "sandwich","orange","broccoli","carrot","hot dog","pizza","donut","cake","chair",
        "couch","potted plant","bed","dining table","toilet","tv","laptop","mouse",
        "remote","keyboard","cell phone","microwave","oven","toaster","sink","refrigerator",
        "book","clock","vase","scissors","teddy bear","hair drier","toothbrush",
    ]

    def __init__(self, model_path: str, conf_threshold: float, target_classes: list):
        self.conf = conf_threshold
        self.target_classes = target_classes  # empty = all classes
        self._backend = None  # "onnx" or "ultralytics"
        self._model = None

        use_onnx = model_path.endswith(".onnx")
        if use_onnx:
            try:
                import onnxruntime as ort
                opts = ort.SessionOptions()
                opts.log_severity_level = 3  # suppress verbose onnxruntime logs
                providers = ["CPUExecutionProvider"]
                self._session = ort.InferenceSession(model_path, sess_options=opts,
                                                     providers=providers)
                self._input_name = self._session.get_inputs()[0].name
                inp_shape = self._session.get_inputs()[0].shape  # e.g. [1, 3, 640, 640]
                self._input_h = inp_shape[2] if len(inp_shape) == 4 else 640
                self._input_w = inp_shape[3] if len(inp_shape) == 4 else 640
                self._backend = "onnx"
                log.info(f"YOLO backend: onnxruntime | model: {model_path} "
                         f"| input: {self._input_w}x{self._input_h}")
            except ImportError:
                log.warning("onnxruntime not found — falling back to ultralytics (torch). "
                            "For RPi: pip install onnxruntime-lite")
                use_onnx = False
            except Exception as e:
                log.error(f"Failed to load ONNX model: {e}")
                raise

        if not use_onnx:
            try:
                from ultralytics import YOLO
                self._model = YOLO(model_path)
                self._backend = "ultralytics"
                log.info(f"YOLO backend: ultralytics | model: {model_path}")
            except Exception as e:
                log.error(f"Failed to load YOLO model (ultralytics): {e}")
                raise

    # ── onnxruntime inference ──────────────────────────────────────────────

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Resize and normalize frame to YOLOv8 input tensor [1, 3, H, W]."""
        img = cv2.resize(frame, (self._input_w, self._input_h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
        return img.transpose(2, 0, 1)[np.newaxis, ...]  # HWC → 1CHW

    def _postprocess_onnx(self, output: np.ndarray, orig_w: int, orig_h: int,
                           cfg: Config) -> Optional[Detection]:
        """
        Parse YOLOv8 ONNX output tensor.
        YOLOv8 export produces shape [1, 84, num_boxes] (4 bbox + 80 classes).
        """
        preds = output[0]  # [84, num_boxes]
        if preds.ndim == 3:
            preds = preds[0]  # strip batch dim if present

        # preds shape: [84, N] — rows 0-3 are cx,cy,w,h; rows 4-83 are class scores
        boxes = preds[:4, :]        # [4, N]
        scores = preds[4:, :]       # [80, N]
        class_ids = np.argmax(scores, axis=0)   # [N]
        confidences = scores[class_ids, np.arange(scores.shape[1])]  # [N]

        # Scale factors back to original frame size
        sx = orig_w / self._input_w
        sy = orig_h / self._input_h

        best: Optional[Detection] = None
        for i in range(confidences.shape[0]):
            conf = float(confidences[i])
            if conf < self.conf:
                continue
            cls_id = int(class_ids[i])
            if self.target_classes and cls_id not in self.target_classes:
                continue

            cx_n, cy_n, w_n, h_n = boxes[:, i]
            x1 = int((cx_n - w_n / 2) * sx)
            y1 = int((cy_n - h_n / 2) * sy)
            x2 = int((cx_n + w_n / 2) * sx)
            y2 = int((cy_n + h_n / 2) * sy)
            area = (x2 - x1) * (y2 - y1)
            if area < cfg.min_target_area:
                continue

            label = self.COCO_NAMES[cls_id] if cls_id < len(self.COCO_NAMES) else str(cls_id)
            d = Detection(cx=(x1 + x2) // 2, cy=(y1 + y2) // 2,
                          area=area, confidence=conf, label=label)
            if best is None or conf > best.confidence:
                best = d
        return best

    # ── public detect() ────────────────────────────────────────────────────

    def detect(self, frame: np.ndarray, cfg: Config) -> Optional[Detection]:
        if self._backend == "onnx":
            inp = self._preprocess(frame)
            output = self._session.run(None, {self._input_name: inp})
            return self._postprocess_onnx(output[0], frame.shape[1], frame.shape[0], cfg)

        # ultralytics path
        results = self._model(frame, conf=self.conf, verbose=False)
        best: Optional[Detection] = None
        for r in results:
            for box in r.boxes:
                cls_id = int(box.cls[0])
                if self.target_classes and cls_id not in self.target_classes:
                    continue
                conf = float(box.conf[0])
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                area = (x2 - x1) * (y2 - y1)
                if area < cfg.min_target_area:
                    continue
                cx = (x1 + x2) // 2
                cy = (y1 + y2) // 2
                label = r.names[cls_id]
                d = Detection(cx=cx, cy=cy, area=area, confidence=conf, label=label)
                if best is None or conf > best.confidence:
                    best = d
        return best


# ─────────────────────────────────────────────
# GUIDANCE
# ─────────────────────────────────────────────

def compute_guidance(det: Detection, frame_w: int, frame_h: int, cfg: Config) -> Tuple[float, float]:
    """
    Compute yaw and pitch corrections from target centroid offset.

    Returns (yaw_error_deg, pitch_error_deg):
      - yaw_error:   positive = target is right of center → yaw right
      - pitch_error: positive = target is below center → pitch down (nose toward target)
    """
    # Normalized offset from frame center: -1.0 (left/top) to +1.0 (right/bottom)
    err_x = (det.cx - frame_w / 2) / (frame_w / 2)
    err_y = (det.cy - frame_h / 2) / (frame_h / 2)

    # Scale to FOV
    yaw_error   =  err_x * (cfg.fov_h / 2)
    pitch_error =  err_y * (cfg.fov_v / 2)   # positive err_y = target below center = pitch down

    # Clamp to max adjustments
    yaw_error   = max(-cfg.max_yaw_adjust,   min(cfg.max_yaw_adjust,   yaw_error))
    pitch_error = max(-cfg.max_pitch_adjust, min(cfg.max_pitch_adjust, pitch_error))

    return yaw_error, pitch_error


# ─────────────────────────────────────────────
# MAVLINK / FC INTERFACE
# ─────────────────────────────────────────────

class FCInterface:
    """
    MAVLink interface to ArduPlane via pymavlink over UART.

    Why pymavlink instead of MAVSDK:
      MAVSDK's offboard API targets PX4's OFFBOARD mode. ArduPlane uses
      GUIDED mode with MAVLink SET_ATTITUDE_TARGET messages directly.
      pymavlink gives us raw MAVLink access and works correctly with ArduPlane.

    Connection string examples:
      serial:///dev/ttyAMA0:57600   → Pi GPIO UART
      udp://127.0.0.1:14550         → SITL / UDP
    """

    def __init__(self, address: str):
        self.address = address
        self._mav = None
        self._current_heading = 0.0
        self._altitude_m = 0.0
        self._flight_mode = ""
        self._telem_task: Optional[asyncio.Task] = None

    async def connect(self):
        _check_pymavlink()
        from pymavlink import mavutil
        # Parse our connection string format into pymavlink format
        addr = self.address.replace("serial://", "").replace("udp://", "udp:")
        log.info(f"Connecting to FC: {addr}")
        self._mav = mavutil.mavlink_connection(addr, baud=57600)
        # Wait for heartbeat (non-blocking via executor)
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, self._mav.wait_heartbeat)
        log.info(f"FC heartbeat received — system {self._mav.target_system} "
                 f"component {self._mav.target_component}")
        self._telem_task = asyncio.create_task(self._telemetry_loop())

    async def _telemetry_loop(self):
        """Background loop: read MAVLink messages and update cached telemetry."""
        loop = asyncio.get_event_loop()
        while True:
            try:
                msg = await loop.run_in_executor(
                    None, lambda: self._mav.recv_match(blocking=True, timeout=0.1)
                )
                if msg is None:
                    continue
                msg_type = msg.get_type()
                if msg_type == "ATTITUDE":
                    self._current_heading = math.degrees(msg.yaw)
                elif msg_type == "GLOBAL_POSITION_INT":
                    self._altitude_m = msg.relative_alt / 1000.0  # mm → m
                elif msg_type == "HEARTBEAT":
                    # Decode custom_mode to flight mode string (ArduPlane specific)
                    # Mode 15 = GUIDED in ArduPlane
                    self._flight_mode = str(msg.custom_mode)
            except Exception as e:
                log.debug(f"Telemetry read error: {e}")
            await asyncio.sleep(0)

    @property
    def current_heading(self) -> float:
        return self._current_heading

    @property
    def altitude_m(self) -> float:
        return self._altitude_m

    async def send_attitude_command(self, pitch_deg: float, yaw_deg: float, thrust: float = 0.6):
        """
        Send MAVLink SET_ATTITUDE_TARGET to ArduPlane in GUIDED mode.
        pitch_deg: negative = nose down
        yaw_deg:   absolute heading (degrees)
        thrust:    0.0–1.0
        """
        if self._mav is None:
            log.warning("FC not connected — skipping attitude command")
            return

        # Convert degrees to radians for quaternion
        pitch_rad = math.radians(pitch_deg)
        yaw_rad   = math.radians(yaw_deg)

        # Build quaternion (roll=0, pitch, yaw)
        cy, sy = math.cos(yaw_rad / 2),   math.sin(yaw_rad / 2)
        cp, sp = math.cos(pitch_rad / 2), math.sin(pitch_rad / 2)
        q = [cy * cp, -sy * sp, cy * sp, sy * cp]  # w, x, y, z

        try:
            self._mav.mav.set_attitude_target_send(
                int(time.time() * 1000) & 0xFFFFFFFF,  # time_boot_ms
                self._mav.target_system,
                self._mav.target_component,
                0b00000100,   # type_mask: ignore roll rate, yaw rate, pitch rate; use attitude + thrust
                q,            # quaternion
                0.0, 0.0, 0.0,  # roll, pitch, yaw rates (ignored)
                thrust
            )
        except Exception as e:
            log.warning(f"Attitude command failed: {e}")

    async def send_guided_position(self, lat: float, lon: float, alt_m: float):
        """Fly to a specific GPS position in GUIDED mode."""
        if self._mav is None:
            return
        try:
            self._mav.mav.mission_item_int_send(
                self._mav.target_system,
                self._mav.target_component,
                0,                          # seq
                3,                          # frame: MAV_FRAME_GLOBAL_RELATIVE_ALT
                16,                         # command: MAV_CMD_NAV_WAYPOINT
                2,                          # current: 2 = guided-mode target
                1,                          # autocontinue
                0, 0, 0, 0,                 # params 1–4
                int(lat * 1e7),
                int(lon * 1e7),
                alt_m
            )
        except Exception as e:
            log.warning(f"Guided position command failed: {e}")

    async def is_in_guided_mode(self) -> bool:
        """
        Check if ArduPlane is in GUIDED mode.
        ArduPlane custom_mode 15 = GUIDED.
        """
        return self._flight_mode == "15"


class SimFCInterface:
    """
    Simulated FC for desktop testing (no physical FC needed).
    Prints commands instead of sending them.
    """

    def __init__(self):
        self._heading = 0.0
        self._altitude = 80.0

    async def connect(self):
        log.info("[SIM] FC interface (no hardware)")

    @property
    def current_heading(self) -> float:
        return self._heading

    @property
    def altitude_m(self) -> float:
        return self._altitude

    async def send_attitude_command(self, pitch_deg: float, yaw_deg: float, thrust: float = 0.6):
        log.info(f"[SIM] Attitude cmd → pitch={pitch_deg:.1f}° yaw={yaw_deg:.1f}° thrust={thrust:.2f}")

    async def is_in_guided_mode(self) -> bool:
        return True  # Always "guided" in sim


# ─────────────────────────────────────────────
# OVERLAY / DEBUG DISPLAY
# ─────────────────────────────────────────────

def draw_overlay(frame: np.ndarray, det: Optional[Detection], lock_count: int,
                 lock_threshold: int, yaw_err: float, pitch_err: float,
                 fps: float = 0.0) -> np.ndarray:
    h, w = frame.shape[:2]
    out = frame.copy()

    # Crosshair at frame center
    cx, cy = w // 2, h // 2
    cv2.line(out, (cx - 30, cy), (cx + 30, cy), (0, 255, 0), 1)
    cv2.line(out, (cx, cy - 30), (cx, cy + 30), (0, 255, 0), 1)

    if det:
        # Target marker
        color = (0, 0, 255) if lock_count >= lock_threshold else (0, 165, 255)
        cv2.circle(out, (det.cx, det.cy), 20, color, 2)
        cv2.line(out, (cx, cy), (det.cx, det.cy), color, 1)

        # Lock indicator
        lock_pct = min(lock_count / lock_threshold, 1.0)
        bar_w = int(200 * lock_pct)
        cv2.rectangle(out, (10, h - 30), (210, h - 10), (50, 50, 50), -1)
        cv2.rectangle(out, (10, h - 30), (10 + bar_w, h - 10), color, -1)
        cv2.putText(out, f"LOCK {lock_count}/{lock_threshold}", (10, h - 35),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # Guidance values
        cv2.putText(out, f"Yaw err:   {yaw_err:+.1f}deg", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(out, f"Pitch err: {pitch_err:+.1f}deg", (10, 80),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        cv2.putText(out, f"Target: {det.label} ({det.confidence:.0%})", (10, 100),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    else:
        cv2.putText(out, "NO TARGET", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (100, 100, 100), 1)

    if lock_count >= lock_threshold:
        cv2.putText(out, "** LOCKED **", (w // 2 - 60, 40),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)

    # FPS counter (top-right)
    if fps > 0:
        fps_text = f"{fps:.1f} FPS"
        cv2.putText(out, fps_text, (w - 100, 20),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

    return out


# ─────────────────────────────────────────────
# MAIN TARGETING LOOP
# ─────────────────────────────────────────────

def _open_camera(cfg: Config, video_path: Optional[str] = None) -> cv2.VideoCapture:
    """
    Open camera or video file with retry logic.
    Returns an opened VideoCapture or raises RuntimeError.
    """
    if video_path:
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise RuntimeError(f"Could not open video file: {video_path}")
        log.info(f"Opened video file: {video_path}")
        return cap

    for attempt in range(1, cfg.camera_open_retries + 1):
        cap = cv2.VideoCapture(cfg.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, cfg.frame_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cfg.frame_height)
        cap.set(cv2.CAP_PROP_FPS, cfg.fps)
        # Minimize internal buffer to reduce pipeline latency (~1 frame vs default 3–5).
        # Critical for real-time guidance — we want the freshest frame, not a stale buffer.
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        if cap.isOpened():
            # Warmup: discard first N frames (auto-exposure settling)
            for _ in range(cfg.camera_warmup_frames):
                cap.read()
            log.info(f"Camera /dev/video{cfg.camera_index} opened on attempt {attempt}")
            return cap
        log.warning(f"Camera open failed (attempt {attempt}/{cfg.camera_open_retries}), "
                    f"retrying in {cfg.camera_retry_delay_s}s...")
        time.sleep(cfg.camera_retry_delay_s)

    raise RuntimeError(f"Could not open camera index {cfg.camera_index} "
                       f"after {cfg.camera_open_retries} attempts")


async def targeting_loop(mode: str, sim: bool, video_path: Optional[str] = None,
                         display: bool = False):
    """
    sim=True:     no FC connection, display overlay (pure desktop/video testing)
    sim=False:    real FC connection
    display=True: show overlay even when sim=False (used for --sitl)
    """
    cfg = CFG
    show_display = sim or display

    # FC interface
    if sim:
        fc = SimFCInterface()
    else:
        fc = FCInterface(cfg.fc_address)
    await fc.connect()

    # Detector
    if mode == "yolo":
        detector = YOLODetector(cfg.yolo_model_path, cfg.yolo_conf_threshold, cfg.yolo_target_classes)
        detect_fn = lambda frame: detector.detect(frame, cfg)
    else:
        detect_fn = lambda frame: detect_color_mask(frame, cfg)

    # Camera / video
    try:
        cap = _open_camera(cfg, video_path)
    except RuntimeError as e:
        log.error(str(e))
        return

    frame_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    is_video_file = video_path is not None
    log.info(f"Source: {'video file' if is_video_file else 'camera'} "
             f"{frame_w}x{frame_h} | Mode: {mode.upper()} | Sim: {sim}")

    lock_count = 0
    consecutive_misses = 0
    yaw_err = 0.0
    pitch_err = 0.0
    # FPS tracking
    _fps_t = time.monotonic()
    _fps_frames = 0
    _fps_display = 0.0

    try:
        while True:
            frame_start = time.monotonic()
            ret, frame = cap.read()
            if not ret:
                if is_video_file:
                    log.info("End of video file.")
                    break
                log.warning("Frame grab failed — skipping.")
                await asyncio.sleep(0.01)
                continue

            # ── FPS counter (update every second) ──
            _fps_frames += 1
            _fps_elapsed = time.monotonic() - _fps_t
            if _fps_elapsed >= 1.0:
                _fps_display = _fps_frames / _fps_elapsed
                _fps_frames = 0
                _fps_t = time.monotonic()

            # ── Detect ──
            det = detect_fn(frame)

            if det:
                yaw_err, pitch_err = compute_guidance(det, frame_w, frame_h, cfg)
                lock_count = min(lock_count + 1, cfg.lock_threshold * 2)  # cap to prevent runaway
                consecutive_misses = 0
            else:
                consecutive_misses += 1
                # Gradual decay on brief misses; hard reset after >30 consecutive misses
                if consecutive_misses > 30:
                    lock_count = 0
                else:
                    lock_count = max(0, lock_count - 1)

            # ── Command (only when locked and in GUIDED mode) ──
            if lock_count >= cfg.lock_threshold:
                in_guided = await fc.is_in_guided_mode()
                if in_guided:
                    target_yaw   = (fc.current_heading + yaw_err) % 360
                    target_pitch = cfg.cruise_pitch - pitch_err  # pitch down = negative

                    # Engagement phase: below threshold altitude → pull up or impact
                    if fc.altitude_m < cfg.engagement_altitude_m:
                        log.info(f"ENGAGEMENT ALTITUDE REACHED ({fc.altitude_m:.1f}m) — pulling up")
                        await fc.send_attitude_command(
                            pitch_deg=cfg.pullup_pitch,
                            yaw_deg=target_yaw,
                            thrust=0.8
                        )
                    else:
                        await fc.send_attitude_command(
                            pitch_deg=target_pitch,
                            yaw_deg=target_yaw,
                            thrust=0.6
                        )
                else:
                    log.debug("Locked but not in GUIDED mode — waiting for pilot switch")

            # ── Display (sim / SITL / desktop only) ──
            if show_display:
                overlay = draw_overlay(frame, det, lock_count, cfg.lock_threshold,
                                       yaw_err, pitch_err, fps=_fps_display)
                cv2.imshow("HK CV Pipeline", overlay)
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    log.info("Quit requested.")
                    break
                elif key == ord('r'):
                    lock_count = 0
                    log.info("Lock count reset.")

            # ── Frame rate throttle (account for processing time) ──
            frame_elapsed = time.monotonic() - frame_start
            sleep_s = (1.0 / cfg.fps) - frame_elapsed
            if sleep_s > 0:
                await asyncio.sleep(sleep_s)

    except KeyboardInterrupt:
        log.info("Interrupted.")
    finally:
        cap.release()
        if show_display:
            cv2.destroyAllWindows()
        log.info("Pipeline stopped.")


# ─────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HK Drone CV Targeting Pipeline")
    parser.add_argument("--mode", choices=["color", "yolo"], default="color",
                        help="Detection mode: 'color' (HSV mask) or 'yolo' (YOLOv8n)")
    parser.add_argument("--sim", action="store_true",
                        help="Simulation mode: display overlay, no FC connection needed")
    parser.add_argument("--sitl", action="store_true",
                        help="SITL mode: display overlay + connect FC at udp://127.0.0.1:14550")
    parser.add_argument("--fc-address", type=str, default=None,
                        help="FC connection string (e.g. serial:///dev/ttyAMA0:57600 or "
                             "udp://127.0.0.1:14550). Overrides Config default.")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--video", type=str, default=None,
                        help="Path to a video file for testing (implies --sim)")
    args = parser.parse_args()

    CFG.camera_index = args.camera

    # --sitl: connect to SITL FC + show display
    if args.sitl:
        CFG.fc_address = "udp://127.0.0.1:14550"
    elif args.fc_address:
        CFG.fc_address = args.fc_address

    # --sitl takes precedence: even with --video, connect to real SITL FC (don't fall back to SimFCInterface)
    sim_mode = args.sim or (args.video is not None and not args.sitl)
    # --sitl always shows display overlay, regardless of sim_mode
    sitl_display = args.sitl

    if not sim_mode:
        _check_pymavlink()

    asyncio.run(targeting_loop(
        mode=args.mode,
        sim=sim_mode,
        video_path=args.video,
        display=sitl_display,
    ))
