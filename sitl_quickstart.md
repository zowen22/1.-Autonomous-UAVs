# ArduPlane SITL Quickstart — HK Build

This lets you test the full Stage 2–3 autonomy stack **before any hardware arrives**.
You get a simulated ArduPlane + GPS + MAVLink telemetry running on your laptop.

---

## Prerequisites

- Python 3.10+ (already needed for cv_pipeline.py)
- MAVProxy or Mission Planner (for ground station)
- ArduPilot SITL binary

---

## 1. Install ArduPilot SITL

### Option A — Native Linux / WSL2 (recommended)

```bash
# Clone ArduPilot
git clone --recurse-submodules https://github.com/ArduPilot/ardupilot.git
cd ardupilot

# Install dependencies (Ubuntu/Debian/WSL2)
Tools/environment_install/install-prereqs-ubuntu.sh -y
. ~/.profile

# Build ArduPlane SITL
./waf configure --board sitl
./waf plane
```

### Option B — Pre-built Docker image (easiest on Windows)

```bash
docker pull ardupilot/ardupilot-dev-base
# Then run SITL inside the container — see ArduPilot SITL Docker docs
```

---

## 2. Launch ArduPlane SITL

```bash
cd ardupilot/ArduPlane
sim_vehicle.py -v ArduPlane --console --map
```

This opens:
- A MAVProxy console (type commands here)
- A map window showing the simulated aircraft

**Default SITL outputs MAVLink on:**
- `udp://127.0.0.1:14550` — primary GCS (Mission Planner connects here)
- `udp://127.0.0.1:14551` — secondary (companion computer / cv_pipeline)

---

## 3. Connect Mission Planner to SITL

1. Open Mission Planner
2. Top-right dropdown: select **UDP**
3. Connect port: **14550**
4. Click Connect

You should see the simulated aircraft on the map with telemetry.

---

## 4. Run the CV Pipeline Against SITL

In a second terminal:

```bash
# Color mask mode (no webcam needed for logic testing — use --video for recorded footage)
python cv_pipeline.py --mode color --sitl --video test_footage.mp4

# Or with webcam (point at an orange target):
python cv_pipeline.py --mode color --sitl
```

`--sitl` connects to `udp://127.0.0.1:14550` and shows the GUI overlay. The pipeline
will send MAVLink attitude commands to the SITL aircraft when it detects a target and
is in GUIDED mode.

> **Note:** SITL uses port 14550 by default. If Mission Planner is already using 14550,
> either close Mission Planner, or connect cv_pipeline to 14551 instead:
> `python cv_pipeline.py --mode color --sitl --fc-address udp://127.0.0.1:14551`

---

## 5. Test Stage 2 — Autonomous Waypoints in SITL

From the MAVProxy console:

```
# Arm and set to AUTO mode
arm throttle
mode auto

# Or set a guided target
mode guided
guided 37.7749 -122.4194 100   # lat lon alt_m — pick a location near default SITL home
```

Or use Mission Planner's Flight Plan view to upload a waypoint mission and watch it execute.

---

## 6. Test Stage 3 — CV GUIDED Override in SITL

1. Launch SITL: `sim_vehicle.py -v ArduPlane --console --map`
2. In MAVProxy: `arm throttle` → `mode guided`
3. Run: `python cv_pipeline.py --mode color --sitl`
4. Point webcam at orange target (or use `--video`)
5. Watch the SITL aircraft yaw/pitch toward the target on the map

The pipeline sends `SET_ATTITUDE_TARGET` MAVLink messages. In SITL you should see
the aircraft respond in the map window within a few locked frames.

---

## 7. Useful MAVProxy Commands

```
mode manual       # manual control
mode fbwa         # fly-by-wire A (stabilized)
mode auto         # execute uploaded mission
mode guided       # accept attitude/position commands from companion computer
mode loiter       # orbit current position
rtl               # return to launch

param set FENCE_ENABLE 0   # disable fence for bench testing
param show SERIAL3_PROTOCOL  # verify companion port config
```

---

## 8. Testing Without SITL (Pure Sim)

If you just want to test the CV pipeline and overlay (no FC at all):

```bash
python cv_pipeline.py --mode color --sim                     # live webcam
python cv_pipeline.py --mode color --sim --video file.mp4   # recorded video
```

This runs entirely offline — no ArduPilot needed. Good for tuning detection params.

---

---

## 9. Automated Stage 2 Mission (sitl_mission.py)

Instead of typing MAVProxy commands manually, use the included mission script:

```bash
# Start SITL first, then in a second terminal:
python sitl_mission.py

# Dry run: print the mission plan without connecting
python sitl_mission.py --dry-run

# If Mission Planner is using 14550, connect cv_pipeline to 14551:
python sitl_mission.py --fc udp://127.0.0.1:14551

# Upload mission without auto-arming (arm manually from GCS):
python sitl_mission.py --no-arm
```

This uploads a 5-waypoint mission (takeoff → 2 cruise WPs → loiter 3 turns → RTL),
arms the aircraft, sets AUTO mode, and prints live telemetry. Good for verifying
Stage 2 logic end-to-end before hardware arrives.

**Tip:** If arming fails with pre-arm errors, disable checks in MAVProxy:
```
param set ARMING_CHECK 0
```

---

## 10. Preflight Check (preflight_check.py)

Before any real flight (or to verify RPi + FC setup), run the preflight script:

```bash
# Full hardware check (camera + FC + GPS + params):
python preflight_check.py

# Sim mode (camera + libraries only, no FC):
python preflight_check.py --sim

# Check against SITL:
python preflight_check.py --fc-address udp://127.0.0.1:14550
```

Checks: camera open/frame read, pymavlink import, FC heartbeat, GPS fix, airspeed
sensor, battery voltage, and critical ArduPlane parameters (SERIAL3_PROTOCOL,
ARSPD_USE, FENCE_ENABLE).

---

## Bug Note: --sitl + --video

cv_pipeline.py was previously buggy when combining `--sitl` and `--video`:
video alone used to force `sim=True`, bypassing the real SITL FC connection.
This is now fixed (as of nightly #3). `--sitl --video test.mp4` now correctly
connects to the SITL FC and uses the video file as the camera source.

```bash
# This now works correctly (SITL FC + video file as camera):
python cv_pipeline.py --mode color --sitl --video test_footage.mp4
```

---

## Resources

- ArduPilot SITL docs: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
- sim_vehicle.py reference: https://ardupilot.org/dev/docs/using-sitl-for-ardupilot-testing.html
- MAVProxy docs: https://ardupilot.org/mavproxy/
