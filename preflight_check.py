"""
HK Drone — Preflight System Check
===================================
Run this on the Raspberry Pi (or desktop with --sim) before every flight.
Checks all hardware subsystems and reports PASS/FAIL for each.

Usage:
  python preflight_check.py                         # full check (real hardware)
  python preflight_check.py --sim                   # sim mode: skip FC/GPS checks
  python preflight_check.py --fc-address udp://127.0.0.1:14550  # SITL check

Exit code: 0 if all checks pass, 1 if any check fails.
"""

import argparse
import sys
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("preflight")

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
WARN = "\033[93m⚠ WARN\033[0m"
SKIP = "\033[94m- SKIP\033[0m"

results: dict[str, str] = {}


def check(name: str, passed: bool | None, detail: str = "", warn_only: bool = False) -> bool:
    if passed is None:
        results[name] = SKIP
        print(f"  {SKIP}  {name}  {detail}")
        return True
    if passed:
        results[name] = PASS
        print(f"  {PASS}  {name}  {detail}")
        return True
    else:
        tag = WARN if warn_only else FAIL
        results[name] = tag
        print(f"  {tag}  {name}  {detail}")
        return warn_only  # WARN = don't fail overall; FAIL = fail overall


def check_camera(camera_index: int = 0) -> bool:
    print("\n[1/4] Camera")
    try:
        import cv2
        cap = cv2.VideoCapture(camera_index)
        opened = cap.isOpened()
        if opened:
            ret, frame = cap.read()
            cap.release()
            ok = ret and frame is not None and frame.size > 0
            return check("Camera open + frame read", ok,
                         f"(index {camera_index}, shape: {frame.shape if ok else 'N/A'})")
        else:
            return check("Camera open", False, f"(index {camera_index} not found)")
    except ImportError:
        return check("opencv-python", False, "(run: pip install opencv-python-headless)")
    except Exception as e:
        return check("Camera", False, str(e))


def check_pymavlink() -> bool:
    print("\n[2/4] pymavlink")
    try:
        import pymavlink  # noqa
        from pymavlink import mavutil  # noqa
        return check("pymavlink import", True)
    except ImportError:
        return check("pymavlink import", False, "(run: pip install pymavlink)")


def check_fc(fc_address: str, timeout_s: int = 10) -> bool:
    print("\n[3/4] Flight Controller (MAVLink)")
    try:
        from pymavlink import mavutil
        log.info(f"Connecting to FC at {fc_address} (timeout {timeout_s}s)...")
        addr = fc_address.replace("serial://", "").replace("udp://", "udp:")
        mav = mavutil.mavlink_connection(addr, baud=57600)
        hb = mav.wait_heartbeat(timeout=timeout_s)
        if hb is None:
            return check("FC heartbeat", False, f"(no heartbeat within {timeout_s}s)")
        check("FC heartbeat", True,
              f"(system {mav.target_system}, component {mav.target_component})")

        # GPS status
        gps_msg = mav.recv_match(type="GPS_RAW_INT", blocking=True, timeout=5)
        if gps_msg:
            fix = gps_msg.fix_type
            sats = gps_msg.satellites_visible
            fix_str = {0: "NO_GPS", 1: "NO_FIX", 2: "2D_FIX", 3: "3D_FIX",
                       4: "DGPS", 5: "RTK_FLOAT", 6: "RTK_FIXED"}.get(fix, str(fix))
            gps_ok = fix >= 3
            check("GPS fix", gps_ok, f"({fix_str}, {sats} sats)", warn_only=not gps_ok)
        else:
            check("GPS fix", False, "(no GPS_RAW_INT message within 5s)", warn_only=True)

        # Airspeed
        aspd_msg = mav.recv_match(type="VFR_HUD", blocking=True, timeout=3)
        if aspd_msg:
            aspd = aspd_msg.airspeed
            check("Airspeed sensor", True, f"({aspd:.1f} m/s — 0 is normal on ground)")
        else:
            check("Airspeed sensor", False, "(no VFR_HUD message — check sensor wiring)", warn_only=True)

        # Battery
        bat_msg = mav.recv_match(type="SYS_STATUS", blocking=True, timeout=3)
        if bat_msg:
            voltage_v = bat_msg.voltage_battery / 1000.0
            current_a = bat_msg.current_battery / 100.0
            bat_ok = voltage_v > 14.0  # rough check for 4S (>14V = not critically low)
            check("Battery voltage", bat_ok, f"({voltage_v:.2f} V, {current_a:.1f} A)",
                  warn_only=True)
        else:
            check("Battery voltage", None, "(no SYS_STATUS)")

        mav.close()
        return True

    except Exception as e:
        check("FC connection", False, str(e))
        return False


def check_mavlink_params(fc_address: str) -> bool:
    """Verify critical ArduPlane parameters are set correctly."""
    print("\n[4/4] ArduPlane Parameters")
    required_params = {
        "SERIAL3_PROTOCOL": (2.0, "must be 2 (MAVLink2) for companion computer"),
        "ARSPD_USE": (1.0, "must be 1 to use airspeed sensor"),
        "FENCE_ENABLE": (1.0, "must be 1 for geofence safety"),
    }
    warn_params = {
        "FRAME_CLASS": (2.0, "should be 2 for fixed wing"),
    }

    try:
        from pymavlink import mavutil
        addr = fc_address.replace("serial://", "").replace("udp://", "udp:")
        mav = mavutil.mavlink_connection(addr, baud=57600)
        mav.wait_heartbeat(timeout=10)

        all_ok = True
        for param_name, (expected, note) in required_params.items():
            mav.mav.param_request_read_send(
                mav.target_system, mav.target_component,
                param_name.encode("utf-8"), -1
            )
            msg = mav.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
            if msg and msg.param_id.strip("\x00") == param_name:
                ok = abs(msg.param_value - expected) < 0.1
                all_ok = check(f"Param {param_name}", ok,
                               f"(got {msg.param_value}, expected {expected} — {note})") and all_ok
            else:
                all_ok = check(f"Param {param_name}", False, "(no response)") and all_ok

        for param_name, (expected, note) in warn_params.items():
            mav.mav.param_request_read_send(
                mav.target_system, mav.target_component,
                param_name.encode("utf-8"), -1
            )
            msg = mav.recv_match(type="PARAM_VALUE", blocking=True, timeout=3)
            if msg and msg.param_id.strip("\x00") == param_name:
                ok = abs(msg.param_value - expected) < 0.1
                check(f"Param {param_name}", ok,
                      f"(got {msg.param_value}, expected {expected} — {note})", warn_only=True)

        mav.close()
        return all_ok

    except Exception as e:
        check("Parameter check", False, str(e))
        return False


def main():
    parser = argparse.ArgumentParser(description="HK Drone Preflight Check")
    parser.add_argument("--sim", action="store_true",
                        help="Sim mode: only check camera and libraries, skip FC checks")
    parser.add_argument("--fc-address", type=str, default="serial:///dev/ttyAMA0:57600",
                        help="FC connection string (default: RPi GPIO UART)")
    parser.add_argument("--camera", type=int, default=0, help="Camera index (default: 0)")
    parser.add_argument("--skip-params", action="store_true",
                        help="Skip ArduPlane parameter verification (faster)")
    args = parser.parse_args()

    print("=" * 55)
    print("  HK Drone — Preflight System Check")
    print(f"  Mode: {'SIM (no FC)' if args.sim else args.fc_address}")
    print("=" * 55)

    passed = True

    passed = check_camera(args.camera) and passed
    passed = check_pymavlink() and passed

    if not args.sim:
        passed = check_fc(args.fc_address) and passed
        if not args.skip_params:
            passed = check_mavlink_params(args.fc_address) and passed
    else:
        print("\n[3/4] Flight Controller — SKIPPED (--sim)")
        print("\n[4/4] ArduPlane Parameters — SKIPPED (--sim)")

    print("\n" + "=" * 55)
    total = len(results)
    failed = sum(1 for v in results.values() if "FAIL" in v)
    warned = sum(1 for v in results.values() if "WARN" in v)
    print(f"  Result: {total - failed - warned} passed, {warned} warnings, {failed} failed")
    if passed:
        print(f"  {PASS}  READY TO FLY")
    else:
        print(f"  {FAIL}  NOT READY — fix failures above before flying")
    print("=" * 55)

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
