# CLAUDE.md — bme68x_bsec3 ESPHome External Component

Developer reference for the `bme68x_bsec3` ESPHome external component. Supports Bosch BME690 and BME688 air quality sensors using the BSEC v3.3.0.0 algorithm library.

## Project Overview

- ESPHome external component providing IAQ (Indoor Air Quality), CO2 equivalent, breath VOC equivalent, gas percentage, and compensated temperature/humidity
- Uses a dedicated FreeRTOS task for BSEC processing (same pattern as the BMV080 component)
- ESP-IDF framework only — no Arduino dependency
- BSEC3 precompiled binary library (`libalgobsec.a`) bundled for ESP32, ESP32-S2, ESP32-S3, ESP32-C2/C3

## Repository Layout

```
esphome-bme690/
├── CLAUDE.md                    # This file
├── example_public.yaml          # Public example config (no credentials)
├── components/
│   └── bme68x_bsec3/
│       ├── __init__.py          # YAML config schema, codegen, BSEC3 library linking
│       ├── sensor.py            # 12 sensor platform definitions
│       ├── text_sensor.py       # IAQ accuracy text sensor
│       ├── bme68x_bsec3.h      # Component class declaration
│       ├── bme68x_bsec3.cpp    # Implementation (FreeRTOS task, BSEC3 integration)
│       ├── bme69x.c            # Bosch BME69x sensor API driver
│       ├── bme69x.h            # Sensor API header
│       ├── bme69x_defs.h       # Sensor API definitions
│       └── bosch/
│           └── bsec3/
│               ├── inc/         # bsec_interface.h, bsec_datatypes.h
│               ├── lib/         # Precompiled libalgobsec.a per architecture
│               │   ├── esp32/
│               │   ├── esp32_s2/
│               │   ├── esp32_s3/
│               │   └── esp32_c2c3/
│               └── config/      # BSEC config blobs per model/voltage/rate/age
│                   ├── bme690/  # 8 configurations
│                   └── bme688/  # 2 configurations
```

## Architecture

- **Two-thread model**: FreeRTOS task (8KB stack, priority 5, pinned to core 1) runs the BSEC algorithm loop. Main ESPHome loop's `update()` reads cached sensor data under mutex and publishes to Home Assistant.
- **BSEC instance**: Dynamically allocated via `bsec_get_instance_size()` (~3272 bytes). BSEC3 is multi-instance (uses `void*` instance pointer, allocated dynamically) — NOT a static global like BSEC1.
- **5-second startup delay** before the BSEC task begins processing.

## Critical Technical Notes

### 1. `#include "esphome/core/defines.h"` MUST be the first include in the .cpp file

Without this, `USE_SENSOR`, `USE_TEXT_SENSOR`, etc. are not defined, causing all sensor pointers and `publish_state()` calls to be compiled out by `#ifdef` guards. The component will appear to work (BSEC data flows, logs show values) but Home Assistant sensors stay "Unknown". This was a multi-hour debugging issue. **Never reorder includes in bme68x_bsec3.cpp.**

### 2. BME69x sensor driver files must be in the component root directory

The files `bme69x.c`, `bme69x.h`, and `bme69x_defs.h` are placed directly in `components/bme68x_bsec3/` for ESPHome auto-compilation. They cannot be moved to a subdirectory without adding extra build configuration.

### 3. BSEC3 config blob embedding

Config blobs are embedded via `cg.progmem_array()` — parsed from the `bsec_iaq.c` files at build time, not compiled as separate C files.

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

### Numeric Sensors (12)

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
| `breath_voc_equivalent` | ppm | Estimated breath VOC (LP only) |
| `gas_percentage` | % | Gas contribution percentage |
| `compensated_temperature` | C | Diagnostic |
| `compensated_humidity` | % | Diagnostic |

### Text Sensor (1)

| Sensor | Values |
|---|---|
| `iaq_accuracy` | "Stabilizing" / "Uncertain" / "Calibrating" / "Calibrated" |

## Hardware Reference

- **Verified setup**: ESP32-S3 devkit + W5500 Ethernet + BME690 at I2C address `0x77`
- **I2C pins**: SCL=GPIO4, SDA=GPIO5
- **Device**: `bme690.local` / `192.168.1.180`

## Build Commands

```bash
esphome compile example.yaml
esphome upload example.yaml --device 192.168.1.180
```

## BSEC3 License

The BSEC library (`libalgobsec.a`) is proprietary Bosch Sensortec software. Users must accept the Bosch BSEC Software License Agreement. The precompiled binary is bundled in this repo for convenience but remains subject to Bosch's terms.
