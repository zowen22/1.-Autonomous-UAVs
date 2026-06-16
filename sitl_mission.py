"""
HK Drone — SITL Stage 2 Mission Script
========================================
Auto-uploads a 5-waypoint test mission to ArduPlane SITL and arms the aircraft.
Verifies Stage 2 autonomy: takeoff → cruise waypoints → loiter → RTL.

Prerequisites:
  - ArduPlane SITL running: sim_vehicle.py -v ArduPlane --console --map
  - pip install pymavlink

Usage:
  python sitl_mission.py                    # upload mission + arm + AUTO
  python sitl_mission.py --dry-run          # print mission only, don't upload
  python sitl_mission.py --fc udp://127.0.0.1:14551  # if 14550 is taken by Mission Planner

What this does:
  1. Connects to SITL via MAVLink
  2. Uploads a test mission (5 WPs around SITL default home)
  3. Arms the aircraft
  4. Sets mode to AUTO
  5. Monitors flight and prints telemetry until RTL complete

The default SITL home is near Canberra, Australia (-35.363, 149.165).
This script builds waypoints around that location.
"""

import argparse
import math
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("sitl_mission")


# ─────────────────────────────────────────────
# MISSION DEFINITION
# ─────────────────────────────────────────────

# Default SITL home: ArduPilot default near Canberra, AU
SITL_HOME_LAT = -35.363262
SITL_HOME_LON = 149.165237
SITL_HOME_ALT_M = 584  # MSL altitude at home

CRUISE_ALT_M = 100   # AGL
LOITER_ALT_M = 120   # AGL


def offset_coords(lat: float, lon: float, north_m: float, east_m: float):
    """Simple flat-earth offset. Good enough for small distances (<5km)."""
    dlat = north_m / 111320.0
    dlon = east_m / (111320.0 * math.cos(math.radians(lat)))
    return lat + dlat, lon + dlon


def build_mission(home_lat: float, home_lon: float) -> list[dict]:
    """
    Build a 5-waypoint test mission:
      WP0: Home (takeoff reference)
      WP1: Takeoff to cruise altitude
      WP2: Cruise north 500m
      WP3: Cruise east 500m
      WP4: Loiter at 1000m north, 500m east
      WP5: RTL (return to home)

    Returns list of dicts with MAVLink mission item fields.
    """
    MAV_FRAME_GLOBAL_RELATIVE_ALT = 3
    MAV_CMD_NAV_WAYPOINT = 16
    MAV_CMD_NAV_TAKEOFF = 22
    MAV_CMD_NAV_LOITER_TURNS = 18
    MAV_CMD_NAV_RETURN_TO_LAUNCH = 20

    wp1_lat, wp1_lon = offset_coords(home_lat, home_lon, 200, 0)
    wp2_lat, wp2_lon = offset_coords(home_lat, home_lon, 500, 0)
    wp3_lat, wp3_lon = offset_coords(home_lat, home_lon, 500, 500)
    wp4_lat, wp4_lon = offset_coords(home_lat, home_lon, 1000, 500)

    mission = [
        # Item 0: Home (reference, not flown to)
        {"seq": 0, "frame": 0, "command": 16, "current": 0, "autocontinue": 1,
         "param1": 0, "param2": 0, "param3": 0, "param4": 0,
         "x": int(home_lat * 1e7), "y": int(home_lon * 1e7), "z": SITL_HOME_ALT_M},
        # Item 1: Takeoff
        {"seq": 1, "frame": MAV_FRAME_GLOBAL_RELATIVE_ALT,
         "command": MAV_CMD_NAV_TAKEOFF, "current": 1, "autocontinue": 1,
         "param1": 15, "param2": 0, "param3": 0, "param4": 0,  # param1 = pitch angle
         "x": int(wp1_lat * 1e7), "y": int(wp1_lon * 1e7), "z": CRUISE_ALT_M},
        # Item 2: Cruise north 500m
        {"seq": 2, "frame": MAV_FRAME_GLOBAL_RELATIVE_ALT,
         "command": MAV_CMD_NAV_WAYPOINT, "current": 0, "autocontinue": 1,
         "param1": 0, "param2": 30, "param3": 0, "param4": 0,  # param2 = acceptance radius
         "x": int(wp2_lat * 1e7), "y": int(wp2_lon * 1e7), "z": CRUISE_ALT_M},
        # Item 3: Cruise east 500m
        {"seq": 3, "frame": MAV_FRAME_GLOBAL_RELATIVE_ALT,
         "command": MAV_CMD_NAV_WAYPOINT, "current": 0, "autocontinue": 1,
         "param1": 0, "param2": 30, "param3": 0, "param4": 0,
         "x": int(wp3_lat * 1e7), "y": int(wp3_lon * 1e7), "z": CRUISE_ALT_M},
        # Item 4: Loiter 3 turns (100m radius)
        {"seq": 4, "frame": MAV_FRAME_GLOBAL_RELATIVE_ALT,
         "command": MAV_CMD_NAV_LOITER_TURNS, "current": 0, "autocontinue": 1,
         "param1": 3, "param2": 0, "param3": 100, "param4": 0,  # param1=turns, param3=radius
         "x": int(wp4_lat * 1e7), "y": int(wp4_lon * 1e7), "z": LOITER_ALT_M},
        # Item 5: RTL
        {"seq": 5, "frame": MAV_FRAME_GLOBAL_RELATIVE_ALT,
         "command": MAV_CMD_NAV_RETURN_TO_LAUNCH, "current": 0, "autocontinue": 1,
         "param1": 0, "param2": 0, "param3": 0, "param4": 0,
         "x": 0, "y": 0, "z": 0},
    ]
    return mission


def print_mission(mission: list[dict], home_lat: float, home_lon: float):
    cmd_names = {16: "WAYPOINT", 22: "TAKEOFF", 18: "LOITER_TURNS", 20: "RTL"}
    print("\nMission waypoints:")
    print(f"  Home: {home_lat:.6f}, {home_lon:.6f}")
    for wp in mission[1:]:  # skip home item
        cmd = cmd_names.get(wp["command"], str(wp["command"]))
        lat = wp["x"] / 1e7
        lon = wp["y"] / 1e7
        alt = wp["z"]
        print(f"  WP{wp['seq']}: {cmd:16s} lat={lat:.6f} lon={lon:.6f} alt={alt}m AGL")
    print()


# ─────────────────────────────────────────────
# MAVLINK OPERATIONS
# ─────────────────────────────────────────────

def connect(fc_address: str, timeout_s: int = 15):
    from pymavlink import mavutil
    addr = fc_address.replace("serial://", "").replace("udp://", "udp:")
    log.info(f"Connecting to {addr}...")
    mav = mavutil.mavlink_connection(addr, baud=57600)
    hb = mav.wait_heartbeat(timeout=timeout_s)
    if hb is None:
        log.error(f"No heartbeat received within {timeout_s}s — is SITL running?")
        log.error("  Start SITL: sim_vehicle.py -v ArduPlane --console --map")
        sys.exit(1)
    log.info(f"Connected — system {mav.target_system} component {mav.target_component}")
    return mav


def upload_mission(mav, mission: list[dict]):
    from pymavlink import mavutil
    log.info(f"Uploading {len(mission)} waypoints...")

    # Clear existing mission
    mav.mav.mission_clear_all_send(mav.target_system, mav.target_component)
    ack = mav.recv_match(type="MISSION_ACK", blocking=True, timeout=5)
    if ack is None or ack.type != 0:
        log.warning("Mission clear ack not received or failed — continuing anyway")

    # Send mission count
    mav.mav.mission_count_send(mav.target_system, mav.target_component, len(mission))

    # Send each waypoint on request
    for _ in range(len(mission) + 5):  # max iterations with buffer
        msg = mav.recv_match(type=["MISSION_REQUEST", "MISSION_REQUEST_INT",
                                    "MISSION_ACK"], blocking=True, timeout=5)
        if msg is None:
            log.error("No mission request received — upload timed out")
            return False
        if msg.get_type() == "MISSION_ACK":
            if msg.type == 0:
                log.info("Mission upload complete ✓")
                return True
            else:
                log.error(f"Mission upload failed: MAV_MISSION_RESULT={msg.type}")
                return False
        seq = msg.seq
        wp = mission[seq]
        mav.mav.mission_item_int_send(
            mav.target_system, mav.target_component,
            wp["seq"], wp["frame"], wp["command"],
            wp["current"], wp["autocontinue"],
            float(wp["param1"]), float(wp["param2"]),
            float(wp["param3"]), float(wp["param4"]),
            wp["x"], wp["y"], float(wp["z"])
        )

    log.error("Mission upload loop exhausted without ACK")
    return False


def set_mode(mav, mode_name: str):
    """Set ArduPlane flight mode by name."""
    ARDU_MODES = {
        "MANUAL": 0, "CIRCLE": 1, "STABILIZE": 2, "TRAINING": 3,
        "ACRO": 4, "FBWA": 5, "FBWB": 6, "CRUISE": 7, "AUTOTUNE": 8,
        "AUTO": 10, "RTL": 11, "LOITER": 12, "TAKEOFF": 13, "AVOID": 14,
        "GUIDED": 15, "INITIALIZING": 16, "QSTABILIZE": 17, "QHOVER": 18,
        "QLOITER": 19, "QLAND": 20, "QRTL": 21,
    }
    mode_id = ARDU_MODES.get(mode_name.upper())
    if mode_id is None:
        log.error(f"Unknown mode: {mode_name}")
        return False

    mav.mav.set_mode_send(
        mav.target_system,
        1,  # MAV_MODE_FLAG_CUSTOM_MODE_ENABLED
        mode_id
    )
    # Wait for heartbeat to confirm mode change
    for _ in range(20):
        hb = mav.recv_match(type="HEARTBEAT", blocking=True, timeout=1)
        if hb and hb.custom_mode == mode_id:
            log.info(f"Mode set to {mode_name} ✓")
            return True
    log.warning(f"Mode set to {mode_name} (no confirmation — may still have worked)")
    return True


def arm(mav, timeout_s: int = 10):
    log.info("Arming...")
    mav.mav.command_long_send(
        mav.target_system, mav.target_component,
        400,  # MAV_CMD_COMPONENT_ARM_DISARM
        0,    # confirmation
        1.0, 0, 0, 0, 0, 0, 0  # param1=1 = arm
    )
    start = time.monotonic()
    while time.monotonic() - start < timeout_s:
        msg = mav.recv_match(type=["COMMAND_ACK", "HEARTBEAT"], blocking=True, timeout=1)
        if msg is None:
            continue
        if msg.get_type() == "HEARTBEAT":
            # Check armed flag in base_mode
            from pymavlink import mavutil
            if msg.base_mode & mavutil.mavlink.MAV_MODE_FLAG_SAFETY_ARMED:
                log.info("Aircraft armed ✓")
                return True
    log.error("Arm failed — check SITL console for pre-arm failures")
    return False


def monitor_flight(mav, duration_s: int = 120):
    """Print telemetry for up to duration_s seconds, return on RTL completion."""
    log.info(f"Monitoring flight (max {duration_s}s). Press Ctrl+C to stop.")
    start = time.monotonic()
    last_print = 0.0

    while time.monotonic() - start < duration_s:
        msg = mav.recv_match(type=["GLOBAL_POSITION_INT", "VFR_HUD", "HEARTBEAT"],
                             blocking=True, timeout=1)
        if msg is None:
            continue

        if msg.get_type() == "VFR_HUD":
            now = time.monotonic()
            if now - last_print >= 2.0:
                print(f"  alt={msg.alt:.1f}m  airspeed={msg.airspeed:.1f}m/s  "
                      f"gndspeed={msg.groundspeed:.1f}m/s  hdg={msg.heading}°  "
                      f"thr={msg.throttle}%")
                last_print = now

        if msg.get_type() == "HEARTBEAT":
            # Mode 11 = RTL in ArduPlane
            if msg.custom_mode == 11:
                log.info("Aircraft in RTL — mission complete ✓")
                return True

    log.info("Monitoring timeout reached.")
    return False


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="HK SITL Stage 2 Mission Script")
    parser.add_argument("--fc", type=str, default="udp://127.0.0.1:14550",
                        help="FC/SITL address (default: udp://127.0.0.1:14550)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print mission only, don't connect or upload")
    parser.add_argument("--home-lat", type=float, default=SITL_HOME_LAT,
                        help="Home latitude override")
    parser.add_argument("--home-lon", type=float, default=SITL_HOME_LON,
                        help="Home longitude override")
    parser.add_argument("--no-arm", action="store_true",
                        help="Upload mission but don't arm/start (manual arm from GCS)")
    args = parser.parse_args()

    mission = build_mission(args.home_lat, args.home_lon)
    print_mission(mission, args.home_lat, args.home_lon)

    if args.dry_run:
        log.info("Dry run — no connection made.")
        return

    try:
        import pymavlink  # noqa
    except ImportError:
        log.error("pymavlink not installed. Run: pip install pymavlink")
        sys.exit(1)

    mav = connect(args.fc)

    if not upload_mission(mav, mission):
        log.error("Mission upload failed.")
        sys.exit(1)

    if args.no_arm:
        log.info("--no-arm: mission uploaded. Arm manually from GCS to start.")
        return

    # Brief pause before arming
    time.sleep(2)

    # Set FBWA first (required before AUTO on some ArduPlane configs)
    set_mode(mav, "FBWA")
    time.sleep(1)

    if not arm(mav):
        log.error("Arming failed. Check SITL console.")
        log.info("Tip: in MAVProxy console run 'param set ARMING_CHECK 0' to disable pre-arm checks for SITL")
        sys.exit(1)

    time.sleep(1)
    set_mode(mav, "AUTO")

    monitor_flight(mav, duration_s=180)
    mav.close()
    log.info("Done.")


if __name__ == "__main__":
    main()
