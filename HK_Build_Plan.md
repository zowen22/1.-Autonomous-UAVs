# Hunter Killer — Autonomous Fixed Wing UAV Build Plan

> **Status:** In Progress | **Started:** May 2026  
> **Build Order Note:** Handoff doc recommends Anti-Air Quad → Recon → HK, but we're starting here. That's fine — more interesting, more complex, more fun.

---

## Needs Zach

These items require your physical action or a decision before work can continue.

1. **Order hardware** — Nothing has been ordered yet. Suggested first order: Zohd Dart XL + Matek H743-Wing V3 + Matek M10Q GPS + Airspeed sensor + ELRS EP2 Rx + SiK telemetry pair. See BOM §3 for full list and updated prices.
2. **Raspberry Pi 5 sourcing** — RPi 5 4GB prices have spiked due to the 2026 RAM shortage (~$80–$120 at current resellers). Consider Orange Pi 5 (~$65–$75) as a cost-stable alternative — it has a built-in NPU and similar performance for OpenCV workloads. Decide before ordering companion computer.
3. **Club field confirmation** — Stage 2+ autonomous flight needs a proper flying site. Confirm your aviation club field is available and whether autonomous flights require advance notice or a safety observer.
4. **Target definition for CV** — Before Stage 3, decide what counts as a "target" for demos. Recommendation: start with a bright orange foam disc (color mask mode) — zero setup, visually obvious, totally safe.

---

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Airframe Options](#2-airframe-options)
3. [Bill of Materials](#3-bill-of-materials)
4. [Staged Autonomy Roadmap](#4-staged-autonomy-roadmap)
5. [CV Targeting Pipeline](#5-cv-targeting-pipeline)
6. [ArduPlane vs. Betaflight](#6-arduplane-vs-betaflight)
7. [Aesthetics & Prop Build](#7-aesthetics--prop-build)
8. [Build Sequence](#8-build-sequence)
9. [Open Questions](#9-open-questions)
10. [Wiring Reference](#10-wiring-reference)
11. [Resources](#11-resources)

---

## 1. Project Overview

Small autonomous fixed-wing UAV inspired by the CoD: Black Ops Hunter Killer. Full autonomous operation: launch, loiter, target acquisition via CV, rapid engagement. Also a prop build for the Comic Con / prop club — aesthetics matter.

### Key Requirements

- Fixed wing (efficiency, speed, loiter time)
- Angular, swept-wing profile matching HK aesthetic
- Hand launch primary; bungee optional
- Autonomous waypoint navigation + loiter
- Dual targeting: GPS waypoint mode AND computer vision mode
- Full autonomy, built across 4 staged milestones

### Design Interpretation

The in-game HK is a thrown quad-rotor, but we're building it as a **fixed-wing flying wing** — the sleek, angular silhouette of real-world loitering munitions (Switchblade, Lancet) combined with the game's hard-edged aesthetic. Fixed wing gives you the loiter time and speed profile that actually sells it.

---

## 2. Airframe Options

All options are flying wing or delta configurations to match the HK profile.

### Option A — Scratch Build Flying Wing ✅ Best Aesthetics

Build a foam board flying wing from scratch. Full control over every angle and profile.

- **Wingspan:** 900–1000mm (36–40") — sweet spot for this mission profile
- **Material:** Dollar Tree foam board (DTFB) or 6mm Depron/EPP
- **Wing sweep:** 35–45° leading edge for that angular HK silhouette
- **Motor:** Pusher config (rear-mounted) — keeps nose clean for camera
- **Reference:** Start from FT Versa Wing or FT Arrow geometry, modify sweep and nose to match HK

**Pros:** Full aesthetic control, cheap, repairable, customizable  
**Cons:** Time investment, requires scratch build confidence

---

### Option B — Off-the-Shelf Flying Wing ✅ Fastest Start

Buy an OTS flying wing, paint and mod it. Get the autonomy stack flying before committing to scratch build.

| Platform | Wingspan | Notes |
|---|---|---|
| **Zohd Dart XL** | 1000mm | Best OTS HK aesthetic match — angular swept wing |
| Skywalker X8 | 1880mm | Massive payload bay, very stable, less aggressive look |
| Zohd Dart 250G | 735mm | Smaller/faster, tighter fit for electronics |
| Mini Talon V2 | 1300mm | V-tail, angular, not pure flying wing |

**Best pick:** Zohd Dart XL. Angular swept profile, adequate bay for RPi 5, strong community.

---

### Option C — Flite Test Arrow / Spear Kit

FT's speed-build kits. Aggressive angular delta silhouette, very close to HK profile. Hours to assemble.

- **FT Arrow:** Swept delta, 900mm, very HK-like from front and top
- **FT Spear:** Speed-optimized, great nose geometry

---

### Airframe Decision

> **Plan:** Buy a Zohd Dart XL now to start autonomy development immediately. Simultaneously design and scratch build Option A for the final prop-grade airframe. Debug autonomy software on the Dart; migrate everything to the scratch build when ready.

---

## 3. Bill of Materials

### 3.1 Airframe & Structure

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| Airframe | Zohd Dart XL Extreme PNP | **$130–$160** | Best OTS HK aesthetic. ⚠️ Price increased — KIT version ~$100 at ReadyMadeRC/BuddyRC |
| *(alt)* | FT Arrow Speed Build Kit | $30–$45 | Scratch build, more accurate aesthetic |
| Prop (pusher) | 7x4 or 8x4.5 APC pusher | $8–$12 | Keeps nose clean |
| Prop adapter | M5 or M6 prop saver | $5 | Match to motor shaft |
| Servo extensions | 150–200mm leads ×4 | $5 | Elevon servos |
| Mounting tape | 3M Dual Lock | $10 | Component mounting |
| Adhesives | Foam-safe CA + 30min epoxy | $15 | Repairs and bonding |

### 3.2 Propulsion

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| Motor | SunnySky X2216 1250KV | $28–$35 | Proven fixed wing pusher |
| *(alt)* | Emax GT2215 1180KV | $25–$32 | Slightly lighter |
| ESC | Hobbywing Skywalker 40A | $22–$28 | BEC included, reliable |
| Battery (primary) | 4S 3300mAh LiPo XT60 | $35–$50 | ~30–45 min flight time |
| Battery (extended) | 4S 5000mAh LiPo XT60 | $55–$70 | 45–60+ min, weight penalty |
| XT60 connectors | 5 pairs | $8 | Spares |
| Battery straps | Non-slip velcro ×3 | $6 | |

### 3.3 Flight Controller & RC Link

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| **Flight Controller** | **Matek H743-Wing V3** | **$90–$140** | **Best fixed wing FC, ArduPlane native. V3 now standard; V2 if you find stock** |
| *(alt)* | Pixhawk 6C Mini | $90–$120 | Official PX4/ArduPilot, pricier |
| GPS Module | Matek M10Q-5883 | $30–$40 | GPS + compass combo, compact |
| *(alt)* | Here3+ GPS | $80–$110 | Higher accuracy, CAN bus |
| Airspeed Sensor | Matek ASPD-7002 | $18–$25 | **Critical for ArduPlane** |
| RC Receiver | ExpressLRS EP2 Rx 2.4GHz | $18–$25 | Pairs with your ELRS TX |
| RC Transmitter | RadioMaster TX16S | $160–$200 | Skip if owned |
| Telemetry Radios | SiK 915MHz pair 100mW | $25–$40 | MAVLink to ground station |

### 3.4 Companion Computer (CV & Autonomy)

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| **Companion Computer** | **Raspberry Pi 5 4GB** | **$80–$120** | ⚠️ **Price up ~40% due to 2026 RAM shortage. Check stock before ordering.** |
| *(alt)* | **Orange Pi 5** | **$65–$75** | **Now the better value: stable price, built-in NPU, 8 TOPS, runs OpenCV fine** |
| *(alt)* | NVIDIA Jetson Orin Nano | $200–$250 | Future-proof, overkill for Stage 3 |
| CV Camera | Arducam IMX477 12MP | $35–$55 | High res for target detection |
| *(alt)* | Raspberry Pi Camera v3 | $25–$35 | Simpler, slightly lower quality |
| Wide angle lens | 120° M12 for IMX477 | $15–$25 | Wider FOV for acquisition |
| MicroSD | SanDisk Extreme 64GB | $15 | Boot + recording |
| UART bridge | Direct UART or USB-serial | $5–$10 | Pi to FC MAVLink link |
| Pi power BEC | 5V 5A BEC from main battery | $12–$18 | Powers Pi from LiPo |

### 3.5 FPV & Recording

| Component | Part | Est. Cost | Notes |
|---|---|---|---|
| FPV Camera | Foxeer Razer Nano | $20–$30 | Forward-facing operator view |
| Video TX | Foxeer Reaper 2000mW analog | $40–$55 | Long range analog FPV |
| *(alt)* | HDZero Whoop Lite digital | $65–$85 | If you want digital FPV |
| Goggles | Fatshark Recon v3 or Skyzone | $80–$150 | Skip if owned |
| HD Recorder | Caddx Walnut or Runcam 2 | $40–$65 | Onboard HD recording |

### 3.6 Cost Summary

| Stage | Scope | Est. Cost |
|---|---|---|
| Stage 1–2 Development | OTS airframe + propulsion + FC + ELRS + GPS + airspeed + telemetry | **$450–$650** |
| Stage 3–4 Full Autonomous | Add Orange Pi 5 (or RPi 5) + CV camera + FPV system | +$200–$350 |
| Scratch Build Airframe | Foam + hardware for aesthetic HK build | +$80–$150 |
| **Full Build Total** | **Everything, all stages** | **$730–$1,150** |

> ⚠️ **Prices updated May 2026.** FC and airframe prices both increased ~20–40% vs. original estimates. The RPi 5 4GB is now $80–$120 due to the LPDDR4 RAM shortage; Orange Pi 5 at ~$70 is now the better value choice for this build.

---

## 4. Staged Autonomy Roadmap

Each stage is a flyable, testable checkpoint. **Do not skip ahead.**

### Stage 1 — Manual Flight + GPS Stabilization

**Goal:** Airframe in the air. Stable FBWA flight. All sensors and comms verified.

**ArduPlane setup:**
1. Flash ArduPlane firmware to Matek H743-Wing via Mission Planner
2. Configure frame type: flying wing (elevon mixing)
3. Calibrate accelerometer, compass, radio
4. Set `ARSPD_FBW_MIN = 12`, `ARSPD_FBW_MAX = 22` (m/s)
5. Tune TECS parameters for pitch and speed control
6. Bench test: motor spin direction, prop orientation (pusher!)
7. Set RC failsafe: RTL on signal loss

**Success criteria:**
- Stable FBWA flight 5+ minutes
- Telemetry streaming to laptop
- RC failsafe triggers RTL correctly

---

### Stage 2 — Autonomous Waypoints + Loiter

**Goal:** ArduPlane AUTO mode. Execute pre-planned mission: launch, cruise waypoints, loiter, RTL.

**Mission planning:**
1. Plan 5-waypoint mission in Mission Planner: takeoff → 3 cruise WPs → loiter → RTL
2. Set loiter radius 100–200m; cruise altitude 80–120m AGL
3. Upload mission via telemetry
4. First AUTO flight: observer on airframe, pilot on TX ready to override

**Key parameters:**
```
WP_RADIUS    = 30      # waypoint acceptance radius (m)
LOITER_RADIUS = 100    # loiter orbit radius (m)
CRUISE_SPEED = 15      # m/s
RTL_ALTITUDE = 100     # m
```

**Success criteria:**
- Completes full autonomous mission without intervention
- Loiter holds within 20m of target radius
- Smooth RTL and approach

---

### Stage 3 — Computer Vision Target Acquisition

**Goal:** RPi 5 running CV pipeline detects ground target, sends bearing corrections to FC via MAVLink. Aircraft steers toward target in GUIDED mode.

**Hardware added:**
- Raspberry Pi 5 (4GB) installed in airframe
- Arducam IMX477 camera, forward/downward facing
- UART: Pi TX/RX → Matek H743 Serial 2 port
- 5V BEC powering Pi from main LiPo

**FC config for companion computer:**
```
SERIAL2_PROTOCOL = 2    # MAVLink2
SERIAL2_BAUD     = 57   # 57600 baud
```

Pilot switches to GUIDED mode via RC channel switch to enable CV override. Full RC authority always available.

**Success criteria:**
- CV pipeline detects target (color marker or YOLO)
- Aircraft visibly steers toward target in GUIDED mode
- Pilot can instantly override via RC

---

### Stage 4 — Full Autonomous Engagement

**Goal:** Complete mission: launch → waypoint cruise → loiter → CV target lock → terminal approach.

**Engagement sequence:**
1. Aircraft loiters at altitude above target area
2. CV detects and classifies target
3. System confirms lock for N consecutive frames (debounce)
4. FC transitions: LOITER → GUIDED
5. Pi issues descending approach vector toward target
6. Terminal phase: nose-down approach, throttle management
7. At threshold altitude: impact (expendable) OR pull-up (recoverable)

**Safety checklist:**
- ⚠️ Fly over unpopulated area — club field strongly recommended
- Set hard geofence: `FENCE_TYPE = all`, `FENCE_ACTION = RTL`
- Dedicated kill switch: RC channel cuts autonomous override instantly
- CV targets = color-coded ground markers or foam cutouts. **Never autonomously target people.**
- Check local regs before Stage 4 — autonomous engagement flights may require authorization

---

## 5. CV Targeting Pipeline

See [`cv_pipeline.py`](cv_pipeline.py) for full implementation.

### Architecture

| Layer | Component | Technology |
|---|---|---|
| Capture | Camera input | Arducam IMX477 via libcamera / OpenCV |
| Detection | Object detection | YOLOv8n (ONNX) or HSV color masking |
| Targeting | Lock logic | Centroid tracking + frame debounce |
| Engagement | Vector computation | Bearing + pitch from frame center offset |
| Command | MAVLink output | MAVSDK-Python → UART → Matek H743 |
| Monitoring | Ground station | MAVLink passthrough + optional RTSP stream |

### Detection Modes

**Mode 1 — Color Mask (implement first, great for testing/demos)**  
HSV color masking in OpenCV. No ML needed, runs at camera FPS, totally reliable. Set up a bright orange foam target; the drone locks and dives. Simple, visually impressive for club demos.

**Mode 2 — YOLOv8n (Stage 3–4 full build)**  
YOLOv8n ONNX runtime on RPi 5: ~15–25 FPS. COCO classes (person, vehicle) or fine-tune on custom targets.

### Development Workflow

1. Build and test CV pipeline on desktop (laptop webcam, recorded video)
2. Port to RPi 5, bench test with live camera and target
3. Ground test: aircraft stationary, verify MAVLink commands sent correctly
4. SITL test: ArduPilot SITL + simulated camera, test full guidance loop
5. Low-altitude flight: GUIDED mode, CV controlling at 30m AGL
6. Full Stage 4 mission

---

## 6. ArduPlane vs. Betaflight

| Capability | ArduPlane | Betaflight |
|---|---|---|
| Autonomous waypoints | ✅ Native, full-featured | ❌ Not supported |
| Loiter / orbit | ✅ Native | ❌ Not supported |
| GPS RTL / failsafe | ✅ Full-featured | ⚠️ Basic GPS rescue only |
| Companion computer (MAVLink) | ✅ Full protocol, well documented | ⚠️ MSP only, very limited |
| Fixed wing flight modes | ✅ FBWA, CRUISE, AUTO, GUIDED, LOITER... | ❌ Quad-tuned only |
| Airspeed sensor | ✅ Native (critical for fixed wing) | ❌ Not supported |
| TECS speed+altitude control | ✅ Native | ❌ Not available |
| Mission planning GCS | ✅ Mission Planner, QGroundControl | ❌ Configurator only |
| Learning curve vs. BF | Steeper initially | Familiar |

**Verdict:** ArduPlane, no contest. The Matek H743-Wing supports both firmware — you can reflash to BF to experiment, but for this build you'll stay on ArduPlane.

---

## 7. Aesthetics & Prop Build

### Paint Scheme

- **Base:** Matte dark gray (Rust-Oleum 2X flat gray or Krylon flat black)
- **Panels:** Flat olive drab or dark earth, asymmetric blocky camo
- **Markings:** Stenciled fictional mil-spec text and unit numbers
- **Weathering:** Dry-brush silver on leading edges, panel wash with thinned black acrylic
- **Warning stripe:** Yellow/black hazard stripe around prop area

### Physical Details

- 3D print or foam-carve angular camera fairing on nose/belly
- Fake sensor bumps and antenna arrays from spare FPV hardware
- WS2812B LED strip inside body for glow effect (low current draw, great at night)
- Optional prop guard shroud shaped to match HK in-game profile

### Flying vs. Static Prop

Consider two versions: a **static display prop** (heavier materials, more surface detail, non-functional electronics) and the **flying functional version**. Don't add so much detailing to the flyer that CG shifts or wing loading blows out.

---

## 8. Build Sequence

| Phase | Task | Est. Time | Dependency |
|---|---|---|---|
| A | Order all components (BOM §3) | 1–2 days | None |
| B | Airframe assembly (Zohd Dart XL) | 1 day | Parts in hand |
| B | Electronics install: FC, ESC, motor, GPS, airspeed, ELRS | 1–2 days | Airframe done |
| C | ArduPlane firmware flash + initial config | 2–4 hours | Electronics installed |
| C | FBWA tune + first flights (Stage 1) | 2–3 sessions | Config complete |
| D | Autonomous waypoint testing (Stage 2) | 1–2 sessions | Stage 1 stable |
| E | RPi 5 install + MAVLink comms verified | 1 day | Stage 2 stable |
| F | CV pipeline development on desktop | 3–5 days | RPi installed |
| G | CV flight integration (Stage 3) | 2–3 sessions | CV pipeline bench-tested |
| H | Full autonomous mission (Stage 4) | 1–2 sessions | Stage 3 stable |
| I | Aesthetic detailing + paint | 2–3 days | Can run parallel to any stage |
| J | Scratch build HK airframe | 1–2 weeks | Electronics proven on OTS platform |

**Total:** ~4–6 weeks on weekends. Stage 1–2 achievable in first 2 weekends.

---

## 9. Open Questions

| Question | Options | Recommendation |
|---|---|---|
| Airframe path | OTS Dart XL vs. FT Arrow vs. full scratch | OTS first, scratch for final |
| CV target definition | Color marker vs. YOLO person/vehicle | Color marker for testing, YOLO for final |
| Engagement type | Kamikaze vs. recoverable + simulated payload | Recoverable strongly recommended |
| Live video downlink | Analog FPV vs. HDZero digital vs. RTSP WiFi | Analog FPV for range; RTSP for demos |
| Companion computer | RPi 5 vs. Jetson Orin Nano vs. Orange Pi 5 | RPi 5 — cost, community, proven |
| Launch method | Hand launch vs. bungee catapult | Hand launch first |
| Landing | Belly on grass vs. parachute vs. hand catch | Belly landing (standard) |

---

## 10. Wiring Reference

### Matek H743-Wing V3 — Key Connections

```
POWER
─────
LiPo XT60 ──→ ESC (power + signal from S1 pad)
LiPo ──→ 5V BEC ──→ Pi 5V/GND (or Orange Pi)
           └──→ FC 5V rail (servo power)

FLIGHT CONTROLLER (Matek H743-Wing V3)
───────────────────────────────────────
S1 (SERVO1)  ──→ ESC signal wire       [motor/throttle]
S2 (SERVO2)  ──→ Left elevon servo
S3 (SERVO3)  ──→ Right elevon servo
UART1 TX/RX  ──→ ELRS EP2 Rx (RC link)
UART2 TX/RX  ──→ SiK 915MHz telemetry radio (to ground station)
UART3 TX/RX  ──→ Raspberry Pi / Orange Pi GPIO UART (MAVLink to companion)
              [Pi: GPIO14/15 = UART0; use /dev/ttyAMA0]
I2C          ──→ Matek M10Q GPS+compass module
ADC/UART4    ──→ Matek ASPD-7002 airspeed sensor (I2C or UART per model)
CAM1         ──→ FPV camera (analog)
VTX          ──→ Foxeer Reaper video TX

COMPANION COMPUTER (RPi 5 or Orange Pi 5)
───────────────────────────────────────────
GPIO UART (TX→FC RX, RX→FC TX, GND shared)  ←→  Matek UART3
CSI/USB      ──→  Arducam IMX477 or Pi Camera v3
5V / GND     ──→  BEC output
```

### ArduPlane Parameter Quick Reference

```
# Flying wing frame
FRAME_CLASS         = 2        # Fixed Wing
ELEVON_OUTPUT       = 4        # Elevon mixing (left = S2, right = S3)

# Airspeed
ARSPD_TYPE          = 1        # MS4525 (Matek ASPD-7002 compatible)
ARSPD_FBW_MIN       = 12       # m/s stall + margin
ARSPD_FBW_MAX       = 22       # m/s max cruise
ARSPD_USE           = 1        # use airspeed for control (not just display)

# TECS (speed+altitude control)
TECS_CLMB_MAX       = 5        # max climb rate m/s (conservative for foam)
TECS_SINK_MIN       = 2        # min sink rate m/s
TECS_PITCH_MAX      = 15       # max pitch up degrees
TECS_PITCH_MIN      = -15      # max pitch down degrees

# Navigation
WP_RADIUS           = 30       # waypoint acceptance radius (m)
LOITER_RADIUS       = 100      # loiter orbit radius (m)
CRUISE_SPEED        = 15       # m/s
RTL_ALTITUDE        = 100      # m AGL

# Companion computer (UART3)
SERIAL3_PROTOCOL    = 2        # MAVLink2
SERIAL3_BAUD        = 57       # 57600

# Geofence
FENCE_ENABLE        = 1
FENCE_TYPE          = 7        # max altitude + radius + return
FENCE_ACTION        = 1        # RTL on breach

# Compass — NOTE: fixed wing does NOT require compass for good performance.
# ArduPlane uses GPS heading at speed. Disable if compass causes issues.
COMPASS_USE         = 0        # optional: disable compass
```

> **Calibration tip:** When calibrating the accelerometer, level the wing chord 2–3° nose-up. This is the normal cruise attitude — ArduPlane uses this as "level" for FBWA mode. Getting this right makes the first flights much smoother.

---

## 11. Resources

### Documentation
- ArduPlane: https://ardupilot.org/plane
- Matek H743-Wing wiring: https://mateksys.com/?portfolio=h743-wing
- Mission Planner: https://ardupilot.org/planner
- MAVSDK-Python: https://mavsdk.mavlink.io
- YOLOv8: https://docs.ultralytics.com

### Community
- ArduPilot Discuss: https://discuss.ardupilot.org
- RCGroups fixed wing forums
- r/diydrones
- Flite Test forums (foam build community)

### Simulation
> **Use SITL before every new autonomous stage. No exceptions.**

- ArduPilot SITL: test all autonomous logic before real flight
- Gazebo / AirSim: 3D sim with camera feed for CV pipeline testing
- FlightGear: optional ArduPlane SITL backend
