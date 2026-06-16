# HK Drone — Stage 1 First Flight Checklist

> Use this when you have hardware in hand and are preparing for the first flight.  
> Work top to bottom. Do not skip sections. Each check has a checkbox — print this or track in a text editor.

---

## Phase 1 — Bench Build & Wiring Verification

Do all of this before any power is applied.

- [ ] **Airframe assembled** — Zohd Dart XL (or scratch build) fully together; control surfaces move freely
- [ ] **CG checked** — Balance point is at ~30% of mean aerodynamic chord from leading edge; add/remove ballast if needed
- [ ] **Motor mount secure** — No play; shaft spins freely by hand; no wobble
- [ ] **Prop NOT installed yet** — Leave off for all bench tests
- [ ] **ESC wired** — ESC power leads direct to LiPo XT60; signal wire to FC S1 pad; BEC output to FC 5V rail
- [ ] **Servos wired** — Left elevon → S2, right elevon → S3 (per wiring diagram in HK_Build_Plan.md §10)
- [ ] **ELRS receiver wired** — UART1 TX→RX, RX→TX, 5V, GND
- [ ] **GPS module wired** — Matek M10Q to I2C port; positioned away from compass-interfering wires
- [ ] **Airspeed sensor wired** — Matek ASPD-7002 to UART4/I2C per Matek pinout; pitot tube clear and pointing forward
- [ ] **SiK telemetry wired** — UART2 TX→RX, RX→TX, 5V, GND; antenna clear of other RF
- [ ] **All connectors secure** — No loose JST/servo connectors; no bare wire near motor or prop path
- [ ] **No shorts** — Continuity check: no 5V-to-GND bridges; no signal-to-power touches

---

## Phase 2 — Firmware Flash & Initial Config

- [ ] **ArduPlane firmware flashed** — Use Mission Planner: "Install Firmware" → Plane → current stable release
- [ ] **Frame type set** — `FRAME_CLASS = 2` (Fixed Wing), `ELEVON_OUTPUT = 4` (elevon mixing, S2=left S3=right)
- [ ] **Accelerometer calibrated** — Level wing chord 2–3° nose-up (cruise attitude); run calibration
- [ ] **Compass calibrated** — Rotate aircraft through all orientations; or set `COMPASS_USE = 0` (not needed for fixed wing at speed)
- [ ] **Radio calibrated** — All sticks and switches; verify stick ranges in Mission Planner
- [ ] **RC failsafe configured** — FC triggers RTL on signal loss: `THR_FAILSAFE = 1`, `THR_FS_VALUE = (below your min throttle)`
- [ ] **Airspeed sensor enabled** — `ARSPD_TYPE = 1`, `ARSPD_USE = 1`; blow gently on pitot in Mission Planner and verify reading
- [ ] **ArduPlane parameters set from HK_Build_Plan.md §10** — ARSPD_FBW_MIN/MAX, TECS_CLMB_MAX, WP_RADIUS, LOITER_RADIUS, CRUISE_SPEED, RTL_ALTITUDE
- [ ] **Geofence enabled** — `FENCE_ENABLE = 1`, `FENCE_TYPE = 7`, `FENCE_ACTION = 1` (RTL on breach); set radius > intended flight area but < field boundary
- [ ] **Companion port configured** (even if RPi not installed yet) — `SERIAL3_PROTOCOL = 2`, `SERIAL3_BAUD = 57`

---

## Phase 3 — Control Surface & Motor Verification (NO PROP)

Do this with battery connected but motor prop removed.

- [ ] **Elevator/elevon direction** — In MANUAL mode: stick back → trailing edge up; stick forward → trailing edge down
- [ ] **Roll/elevon direction** — Stick right → right elevon up, left elevon down (and vice versa)
- [ ] **FBWA stabilization direction** — Hold aircraft nose-down → elevons should deflect trailing edge DOWN (to pitch up). Hold nose-up → elevons should deflect UP (to pitch down). **If reversed, set `ELEVON_REVERSE = 1` or flip individual servo reversal in ArduPlane config.**
- [ ] **Throttle direction** — Stick forward → motor spins faster; stick back → motor stops (not reversed)
- [ ] **Motor direction** — For pusher config, prop should push air REARWARD. If wrong, swap any two motor phase wires on ESC.
- [ ] **Telemetry streaming** — Open Mission Planner; connect via SiK radio; verify GPS position, altitude, attitude, airspeed all reading
- [ ] **GPS lock acquired** — Take FC outside; verify 3D fix (≥6 sats); note home position is set

---

## Phase 4 — Pre-Flight Field Checks (at the flying site)

- [ ] **Preflight script passes** — `python preflight_check.py --fc-address serial:///dev/ttyAMA0:57600` (when RPi installed) OR verify manually via Mission Planner
- [ ] **Battery charged** — 4S LiPo at storage charge or full; no puffing; voltage > 16.0V at rest
- [ ] **Prop installed correctly** — Pusher prop (trailing edge faces forward); tight on shaft; spinner on (if used)
- [ ] **CG re-checked with all electronics and battery** — Still at 30% MAC; adjust battery fore/aft as needed
- [ ] **All hatches/compartments closed** — Electronics bay secure; no loose foam panels
- [ ] **Control surfaces move freely** — No binding after assembly; respond to TX inputs correctly
- [ ] **Mode switches tested** — FBWA, MANUAL, RTL all on distinct switch positions; know which is which before you throw it
- [ ] **Kill switch / disarm** — Know which switch/combo immediately disarms motor; test on ground
- [ ] **RC range check** — Walk 30m with aircraft; verify no failsafe triggers; sticks respond
- [ ] **Wind check** — First flights in ≤ 15 mph wind; if gusty, postpone
- [ ] **Clear runway/grass area** — 30m+ clear in the direction you're throwing; people and objects clear

---

## Phase 5 — First Flight Sequence (Stage 1)

**First throw is always FBWA mode.** Do not attempt AUTO on first flight.

1. Arm aircraft (arm throttle; TX arm gesture or Mission Planner arm button)
2. Confirm FBWA mode active on OSD/Mission Planner
3. **Throttle to 70%**, level throw into wind, release cleanly — do not hold back on the aircraft
4. Let the aircraft establish level flight; don't over-correct immediately
5. Trim pitch and roll (small adjustments) until it flies hands-off
6. Test rudder/elevon response — small inputs only
7. Test RTL: switch to RTL mode, verify aircraft turns back toward home; **switch back to FBWA before it gets too close**
8. Land: reduce throttle, glide slope approach, flare 1–2m above ground
9. **After first flight:** Note any trim corrections needed; check that all connections are still secure after the vibration

---

## Stage 1 Success Criteria

Before moving to Stage 2:

- [ ] Stable, hands-off FBWA flight for 5+ minutes
- [ ] Telemetry streaming correctly to laptop during flight
- [ ] RTL tested and confirmed (returns to home heading)
- [ ] RC failsafe tested (disable TX → aircraft enters RTL within 2s)
- [ ] No component failures, loose wires, or overheating after flight

---

## Notes Column

_(add observations after each check)_

| Check | Notes |
|---|---|
| CG position | |
| Trim corrections | |
| Motor/ESC temps | |
| Battery voltage after flight | |
| Airspeed sensor accuracy | |
| GPS lock time | |

---

*Created: 2026-06-01 (nightly #4). Reference: HK_Build_Plan.md §4 (Staged Autonomy Roadmap), §10 (Wiring Reference).*
