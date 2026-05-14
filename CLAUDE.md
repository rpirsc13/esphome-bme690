# CLAUDE.md — bme68x_bsec3 ESPHome External Component

Developer reference for the `bme68x_bsec3` ESPHome external component. Supports Bosch BME690 and BME688 air quality sensors using the BSEC v3.3.0.0 algorithm library.

## Project Overview

- ESPHome external component providing IAQ (Indoor Air Quality), CO2 equivalent, breath VOC equivalent, gas percentage, and compensated temperature/humidity
- Uses a dedicated FreeRTOS task for BSEC processing (same pattern as the BMV080 component)
- ESP-IDF framework only — no Arduino dependency
- **No Bosch software is committed to this repo.** The build downloads it: the proprietary BSEC3 library (`libalgobsec.a`, headers, config blobs) from Bosch Sensortec, and the BSD-3-Clause BME69x SensorAPI from GitHub. Downloaded BSEC binaries are verified against pinned SHA-256 checksums; the BSEC download is gated on `accept_bosch_license: true`.

## Repository Layout

```
esphome-bme690/
├── CLAUDE.md                    # This file
├── LICENSE                      # MIT (component code only)
├── NOTICE                       # Third-party attribution (downloaded deps)
├── example_public.yaml          # Public example config (no credentials)
├── components/
│   └── bme68x_bsec3/
│       ├── __init__.py          # Config schema, codegen, dependency download
│       ├── sensor.py            # 12 sensor platform definitions
│       ├── text_sensor.py       # IAQ accuracy text sensor
│       ├── bme68x_bsec3.h       # Component class declaration
│       ├── bme68x_bsec3.cpp     # Implementation (FreeRTOS task, BSEC3 integration)
│       └── bme69x.{c,h}, bme69x_defs.h  # Downloaded at build time (.gitignored)
```

**Nothing Bosch-owned is committed.** At build time `__init__.py` downloads:
- BSEC3 (`libalgobsec.a`, headers, config blobs) → `.esphome/bme68x_bsec3/bsec_v3.3.0.0/`
  (ESPHome data dir), extracted from the official Bosch zip and SHA-256 verified.
- BME69x SensorAPI (`bme69x.c/.h/_defs.h`) → into the component dir, so ESPHome
  auto-compiles `bme69x.c` (see Critical Technical Note #2).

## Architecture

- **Two-thread model**: FreeRTOS task (8KB stack, priority 5, pinned to core 1) runs the BSEC algorithm loop. Main ESPHome loop's `update()` reads cached sensor data under mutex and publishes to Home Assistant.
- **BSEC instance**: Dynamically allocated via `bsec_get_instance_size()` (~3272 bytes). BSEC3 is multi-instance (uses `void*` instance pointer, allocated dynamically) — NOT a static global like BSEC1.
- **5-second startup delay** before the BSEC task begins processing.

## Critical Technical Notes

### 1. `#include "esphome/core/defines.h"` MUST be the first include in the .cpp file

Without this, `USE_SENSOR`, `USE_TEXT_SENSOR`, etc. are not defined, causing all sensor pointers and `publish_state()` calls to be compiled out by `#ifdef` guards. The component will appear to work (BSEC data flows, logs show values) but Home Assistant sensors stay "Unknown". This was a multi-hour debugging issue. **Never reorder includes in bme68x_bsec3.cpp.**

### 2. BME69x sensor driver files must be in the component root directory

The files `bme69x.c`, `bme69x.h`, and `bme69x_defs.h` must sit directly in `components/bme68x_bsec3/` for ESPHome to auto-compile `bme69x.c`. They cannot be moved to a subdirectory without adding extra build configuration. They are **not committed** — `_download_dependencies()` in `__init__.py` downloads them there at config-validation time (and they are `.gitignored`). This works because ESPHome enumerates a component's source files dynamically (`loader.py` `resources` property) at the copy stage, which runs *after* validation.

### 3. BSEC3 config blob embedding

Config blobs are embedded via `cg.progmem_array()` — parsed from the downloaded `bsec_iaq.c` files at build time, not compiled as separate C files.

### 4. Config blob naming convention

Format: `{model}_iaq_{voltage}v_{sample_rate}s_{operating_age}d`

- **Voltage**: `18v` (1.8V) or `33v` (3.3V)
- **Sample rate**: `3s` (LP — low power) or `300s` (ULP — ultra-low power)
- **Operating age**: `4d` (4 days) or `28d` (28 days)

### 5. BME688 restrictions

Only 3.3V and 28-day configs are available in BSEC3 for the BME688. The BME690 has all 8 combinations.

### 6. I2C callbacks from FreeRTOS task

ESP-IDF's I2C driver is thread-safe, so ESPHome's `I2CDevice` read/write methods work correctly from the BSEC task without additional synchronization.

### 7. State persistence

State is saved via ESPHome preferences (NVS) every 6 hours. The state blob is max 197 bytes. Hash key: `0xB5EC0003`.

### 8. TVOC equivalent sensor

Only available in LP sample rate (3s), not ULP (300s).

### 9. W5500 Ethernet buffer overflow

API encryption combined with multiple sensor publishes can overflow the W5500 Ethernet buffer, observed as `CONNECTION_CLOSED` errors every update cycle. This has been resolved but is worth noting for future debugging.

## BSEC3 API Flow

```
1. bsec_get_instance_size()          -> malloc instance
2. bsec_init(instance)
3. bsec_set_configuration(instance, config_blob, ...)
4. bsec_set_state(instance, saved_state, ...)   -- if available from NVS
5. bsec_update_subscription(instance, requested_outputs, ...)
6. Loop:
   a. bsec_sensor_control(instance, timestamp_ns, &settings)
   b. Configure BME69x hardware per settings
   c. bme69x_get_data()
   d. bsec_do_steps(instance, inputs, outputs)
7. Periodically: bsec_get_state(instance, ...) -> save to NVS
```

## Exposed Sensors

### Numeric Sensors (13)

| Sensor | Unit | Notes |
|---|---|---|
| `temperature` | C | Compensated by BSEC |
| `humidity` | % | Compensated by BSEC |
| `pressure` | hPa | Converted from Pa |
| `gas_resistance` | Ohm | Raw sensor reading |
| `iaq` | 0-500 | Indoor Air Quality index |
| `iaq_accuracy` | 0-3 | Numeric accuracy level |
| `iaq_static` | 0-500 | Static IAQ (no recent history weighting) |
| `co2_equivalent` | ppm | Estimated CO2 |
| `breath_voc_equivalent` | ppm | **Not available in IAQ mode** — always 0. Kept for BSEC2 compatibility. |
| `tvoc_equivalent` | ppb | Total VOC equivalent (LP mode only) |
| `gas_percentage` | % | Gas contribution percentage |
| `raw_temperature` | C | Diagnostic — uncompensated, includes sensor self-heating |
| `raw_humidity` | % | Diagnostic — uncompensated, cross-influenced by heater |

### Important: Breath VOC vs TVOC Equivalent

BSEC3 in IAQ mode does NOT output `BSEC_OUTPUT_BREATH_VOC_EQUIVALENT` (sensor ID 4). Subscribing to it crashes `bsec_update_subscription()`. Use `tvoc_equivalent` instead — this maps to `BSEC_OUTPUT_TVOC_EQUIVALENT` (sensor ID 31), available in LP mode only.

### Available BSEC3 IAQ Mode Subscriptions (reference)

The Bosch reference code subscribes to exactly these outputs in IAQ mode:
1. RAW_PRESSURE (7)
2. RAW_TEMPERATURE (6)
3. RAW_HUMIDITY (8)
4. RAW_GAS (9)
5. IAQ (1)
6. SENSOR_HEAT_COMPENSATED_TEMPERATURE (14)
7. SENSOR_HEAT_COMPENSATED_HUMIDITY (15)
8. STATIC_IAQ (2)
9. CO2_EQUIVALENT (3)
10. STABILIZATION_STATUS (12)
11. RUN_IN_STATUS (13)
12. GAS_PERCENTAGE (21)
13. TVOC_EQUIVALENT (31) — LP mode only

**NOT available in IAQ mode**: BREATH_VOC_EQUIVALENT (4), COMPENSATED_GAS (18)

### Text Sensors (2)

| Sensor | Values |
|---|---|
| `iaq_accuracy` | "Stabilizing" / "Uncertain" / "Calibrating" / "Calibrated" |
| `iaq_description` | "Excellent" / "Good" / "Lightly Polluted" / "Moderately Polluted" / "Heavily Polluted" / "Severely Polluted" / "Extremely Polluted" |

## Hardware Reference

- **Verified setup**: ESP32-S3 devkit + W5500 Ethernet + BME690 at I2C address `0x77`
- **I2C pins**: SCL=GPIO4, SDA=GPIO5
- **Device**: `bme690.local` / `192.168.1.180`

## Build Commands

```bash
esphome compile example.yaml
esphome upload example.yaml --device 192.168.1.180
```

## Licensing

- **Component code** (this repo): MIT — see `LICENSE`.
- **BSEC library**: proprietary Bosch Sensortec software. **Not committed** — downloaded from Bosch at build time. Gated on `accept_bosch_license: true` (a `cv.Required` option validated by `_accept_bosch_license`); the build fails otherwise. Downloaded binaries are SHA-256 verified against pinned hashes in `__init__.py`.
- **BME69x SensorAPI**: BSD-3-Clause — also not committed, downloaded from GitHub at build time.
- See `NOTICE` for full third-party attribution.

To bump the BSEC version: update `BSEC3_VERSION`, `BSEC3_URL`, and the `BSEC3_LIB_SHA256` hashes in `__init__.py`. To bump the SensorAPI: update `BME69X_API_VERSION`.

## License Compliance Record

License compliance for the bundled Bosch dependencies was a deliberate, sustained effort on this project — not an afterthought. This section is the record of that work, the reasoning behind each decision, and how each step was verified. Maintainers must not regress any of these measures.

### Starting point (the problem)

Early revisions committed Bosch's proprietary BSEC `libalgobsec.a` binaries, BSEC headers, and BSEC config blobs directly into version control under `components/bme68x_bsec3/bosch/`. This put Bosch's proprietary software in the repository and its git history, with no accompanying license text, no provenance, and no separation from the MIT-licensed component code. The BME69x SensorAPI (BSD-3-Clause) was also vendored in-tree.

### Measures taken

Each item below was implemented, reviewed, and committed as a distinct, intentional step:

1. **Explicit license boundary in the README** — added a prominent warning block stating BSEC is proprietary Bosch Sensortec software, that no rights are granted by this repository, that it may only be used with BME688/BME690 sensors, and that it must not be extracted/modified/reverse-engineered/sublicensed/redistributed except as Bosch permits.
2. **Added a real `LICENSE` file** — MIT, with a preamble that explicitly scopes it to *only* the repository's own source code and disclaims any coverage of Bosch software. (Previously the README claimed "MIT" with no LICENSE file present at all.)
3. **Added a `NOTICE` file** — full third-party attribution for both Bosch dependencies: copyright holders, license type, where each comes from, the proprietary-use restrictions, and SHA-256 checksums.
4. **Investigated whether the binary could be obtained legitimately at build time** — confirmed Bosch publishes BSEC v3.3.0.0 at a stable, un-gated direct URL on their own CDN, and that the four committed `libalgobsec.a` files were bit-for-bit identical to that official release (verified by SHA-256). This established that a download-at-build-time model was both possible and faithful to Bosch's distribution.
5. **Removed all Bosch software from version control** — `git rm` of the entire `bosch/` tree (binaries, headers, 26 config blobs) and the `bme69x.*` SensorAPI files. The repository now contains *only* the MIT component code. The downloaded copies are `.gitignored` so they cannot be re-committed accidentally.
6. **Build-time download instead of redistribution** — `_download_dependencies()` in `__init__.py` fetches BSEC directly from Bosch's official URL and the SensorAPI from Bosch's GitHub repo. This repository never redistributes Bosch software; it points the build at Bosch's own distribution.
7. **Affirmative license-acceptance gate** — `accept_bosch_license` is a `cv.Required` YAML option; the build fails with a message linking to Bosch's license agreement unless the user sets it to `true`. The proprietary download does not happen until the user has affirmatively accepted Bosch's terms.
8. **Integrity / provenance verification** — every downloaded `libalgobsec.a` is checked against a pinned SHA-256 hash before it is linked; a mismatch fails the build. The SensorAPI is pinned to a specific release tag. This both detects tampering and proves the binaries are the unmodified Bosch release.
9. **Version-bump procedure documented** — the "Licensing" section above records exactly which constants to update so future version bumps keep the checksums and provenance honest.
10. **Redistribution language reviewed and tightened** — the README's statements about redistributing firmware that includes BSEC were revised to direct users to review Bosch's license themselves rather than make absolute claims.

### Verification performed

- Clean build from an empty cache on ESP32-S3: download → extract → SHA-256 verify → compile → link all succeed.
- Negative tests: a corrupted cached binary fails the build with a checksum-mismatch error; a missing or `false` `accept_bosch_license` fails validation with a clear license message.
- Confirmed the three downloaded BME69x SensorAPI files at tag `v1.1.0` are byte-identical to the versions previously vendored.

### Net effect

The repository ships only its own MIT-licensed code. Bosch's proprietary library is never stored or redistributed here, is fetched from Bosch's own servers, is integrity-checked, and is only obtained after the user has explicitly accepted Bosch's license. The BSD-3-Clause SensorAPI is attributed in `NOTICE` and fetched from Bosch's GitHub. (Note: the historical commits before this work still contain the old `bosch/` tree — a git history rewrite would be required to remove it from history entirely, and has not been done.)
