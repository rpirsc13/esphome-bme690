# esphome-bme690

ESPHome external component for **BME690** and **BME688** air quality sensors using Bosch's BSEC v3.3.0.0 algorithm library.

Drop-in sensor platform providing Indoor Air Quality (IAQ), estimated CO2, VOC, temperature, humidity, and barometric pressure. Supports ESP32, ESP32-S2, ESP32-S3, ESP32-C2, ESP32-C3, and ESP32-C6. **ESP-IDF framework required.**

---

> **WARNING: BSEC License Agreement Required**
>
> This component depends on the **Bosch BSEC v3.3.0.0** algorithm library (`libalgobsec.a`), which is **proprietary software** owned by Bosch Sensortec GmbH.
>
> **This repository does not contain and does not redistribute the BSEC library.** Instead, the build downloads it directly from Bosch Sensortec the first time you compile. You must still review and accept the **Bosch Sensortec Software License Agreement** yourself — downloading the library does not grant you any license to it. You confirm acceptance by setting `accept_bosch_license: true` in your YAML configuration; the build fails until you do.
>
> **Review and accept the license terms at:**
> https://www.bosch-sensortec.com/software-tools/software/bme688-and-bme690-software/
>
> No rights to Bosch software are granted by this repository. If you do not or cannot accept Bosch's terms, do not use this component.
>
> The Bosch BSEC library may only be used with Bosch BME688/BME690 sensors and may not be extracted, modified, reverse engineered, sublicensed, or redistributed separately except as permitted by Bosch.
>
> **Firmware binaries that include BSEC cannot be redistributed** per the Bosch license.

---

## Supported Hardware

### Sensors

| Sensor | Status |
|--------|--------|
| BME690 | Verified |
| BME688 | Supported (limited configurations) |

### MCUs

ESP32, ESP32-S2, ESP32-S3, ESP32-C2, ESP32-C3, ESP32-C6

All targets require the **ESP-IDF framework** (not Arduino).

## Quick Start

```yaml
external_components:
  - source: github://sweitzja/esphome-bme690
    components: [bme68x_bsec3]

i2c:
  scl: GPIO4
  sda: GPIO5

bme68x_bsec3:
  model: bme690
  accept_bosch_license: true   # required — see the warning above
  address: 0x77

sensor:
  - platform: bme68x_bsec3
    temperature:
      name: "Temperature"
    humidity:
      name: "Humidity"
    pressure:
      name: "Pressure"
    iaq:
      name: "IAQ"

text_sensor:
  - platform: bme68x_bsec3
    iaq_accuracy:
      name: "IAQ Accuracy"
```

## Full Configuration Reference

```yaml
bme68x_bsec3:
  model: bme690                 # bme690 or bme688
  accept_bosch_license: true    # required — confirms acceptance of Bosch's BSEC license
  address: 0x77                 # 0x77 (default) or 0x76
  supply_voltage: 3.3V          # 3.3V or 1.8V
  sample_rate: LP               # LP (3s) or ULP (300s)
  operating_age: 28d            # 4d or 28d
  temperature_offset: 0         # Heat compensation offset (°C)
  state_save_interval: 6h       # BSEC calibration save interval
```

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `bme690` | Sensor model: `bme690` or `bme688` |
| `accept_bosch_license` | *(required)* | Must be `true`. Confirms you have accepted the [Bosch BSEC Software License Agreement](https://www.bosch-sensortec.com/software-tools/software/bme688-and-bme690-software/). The build fails without it. |
| `address` | `0x77` | I2C address: `0x77` or `0x76` |
| `supply_voltage` | `3.3V` | Sensor supply voltage: `3.3V` or `1.8V` |
| `sample_rate` | `LP` | `LP` = Low Power (3s cycle), `ULP` = Ultra Low Power (300s cycle) |
| `operating_age` | `28d` | Algorithm training period: `4d` or `28d` |
| `temperature_offset` | `0` | Compensation for self-heating, in degrees Celsius |
| `state_save_interval` | `6h` | How often BSEC calibration state is saved to flash |

## Build-Time Downloads

This repository contains only the ESPHome component code (MIT licensed). The Bosch dependencies are **downloaded automatically on first compile** — nothing Bosch-owned is committed to this repository:

| Dependency | License | Source | Cached to |
|---|---|---|---|
| BSEC v3.3.0.0 (`libalgobsec.a`, headers, config blobs) | Proprietary (Bosch) | [Bosch Sensortec download](https://www.bosch-sensortec.com/software-tools/software/bme688-and-bme690-software/) | ESPHome data dir (`.esphome/bme68x_bsec3/`) |
| BME69x SensorAPI v1.1.0 (`bme69x.c/.h/_defs.h`) | BSD-3-Clause | [boschsensortec/BME690_SensorAPI](https://github.com/boschsensortec/BME690_SensorAPI) | component directory |

The downloaded BSEC binaries are verified against pinned SHA-256 checksums (see [Verifying the BSEC download](#verifying-the-bsec-download)); a mismatch fails the build. The BSEC download requires `accept_bosch_license: true` — see the warning at the top of this file.

## All Available Sensors

### Air Quality Sensors

#### `iaq` -- Indoor Air Quality Index

- **Unit:** IAQ (0--500 scale)
- **Description:** Composite air quality index derived from the gas sensor response via the BSEC algorithm. 0 represents clean air, 500 represents heavily polluted air.

| IAQ Range | Quality | Meaning |
|-----------|---------|---------|
| 0--50 | Excellent | Clean air |
| 51--100 | Good | Acceptable |
| 101--150 | Lightly Polluted | Sensitive groups may be affected |
| 151--200 | Moderately Polluted | Everyone may notice effects |
| 201--250 | Heavily Polluted | Health alert |
| 251--350 | Severely Polluted | Emergency conditions |
| 351--500 | Extremely Polluted | Dangerous |

```yaml
sensor:
  - platform: bme68x_bsec3
    iaq:
      name: "IAQ"
```

#### `iaq_static` -- Stabilized IAQ

- **Unit:** IAQ (0--500 scale)
- **Description:** A stabilized version of the IAQ index. Less responsive to rapid changes but more accurate over longer time periods. Preferred for dashboards and automations where stability matters more than responsiveness.

```yaml
sensor:
  - platform: bme68x_bsec3
    iaq_static:
      name: "IAQ (Static)"
```

#### `iaq_accuracy` (numeric) -- Calibration Status

- **Unit:** Numeric, 0--3
- **Description:** Indicates the current calibration state of the BSEC algorithm.

| Value | Label | Meaning |
|-------|-------|---------|
| 0 | Stabilizing | Sensor just powered on, warming up (~5 minutes) |
| 1 | Uncertain | Background model is building |
| 2 | Calibrating | Calibration in progress, readings improving |
| 3 | Calibrated | Fully calibrated, highest accuracy (~24--48 hours) |

```yaml
sensor:
  - platform: bme68x_bsec3
    iaq_accuracy:
      name: "IAQ Accuracy (Numeric)"
```

#### `co2_equivalent` -- Estimated CO2

- **Unit:** ppm
- **Description:** Estimated equivalent CO2 concentration derived from the gas sensor. Not a direct CO2 measurement but a correlation based on VOC levels.

```yaml
sensor:
  - platform: bme68x_bsec3
    co2_equivalent:
      name: "CO2 Equivalent"
```

#### `breath_voc_equivalent` -- Breath VOC (Legacy)

- **Unit:** ppm
- **Description:** Legacy BSEC2-compatible breath VOC sensor. **Not available in IAQ mode** -- always reads 0. Use `tvoc_equivalent` instead.

#### `tvoc_equivalent` -- Total VOC Equivalent

- **Unit:** ppb (parts per billion)
- **Description:** Estimated Total Volatile Organic Compound concentration. This is the BSEC3 replacement for breath VOC. **Only available in LP sample rate mode** (not ULP).

```yaml
sensor:
  - platform: bme68x_bsec3
    tvoc_equivalent:
      name: "TVOC"
```

#### `gas_percentage` -- Gas Sensor Response

- **Unit:** %
- **Description:** Gas sensor response expressed as a percentage of its operating range.

```yaml
sensor:
  - platform: bme68x_bsec3
    gas_percentage:
      name: "Gas Percentage"
```

### Environmental Sensors

#### `temperature` -- Temperature

- **Unit:** degrees C
- **Description:** Heat-compensated temperature reading. Apply `temperature_offset` in the platform configuration to correct for self-heating of the sensor and enclosure.

```yaml
sensor:
  - platform: bme68x_bsec3
    temperature:
      name: "Temperature"
```

#### `humidity` -- Relative Humidity

- **Unit:** %
- **Description:** Heat-compensated relative humidity reading.

```yaml
sensor:
  - platform: bme68x_bsec3
    humidity:
      name: "Humidity"
```

#### `pressure` -- Barometric Pressure

- **Unit:** hPa
- **Description:** Atmospheric pressure reading from the integrated barometric pressure sensor.

```yaml
sensor:
  - platform: bme68x_bsec3
    pressure:
      name: "Pressure"
```

#### `gas_resistance` -- Raw Gas Resistance

- **Unit:** Ohm
- **Description:** Raw resistance value from the gas sensor element. Useful for debugging or custom algorithms. Not processed by BSEC.

```yaml
sensor:
  - platform: bme68x_bsec3
    gas_resistance:
      name: "Gas Resistance"
```

### Diagnostic Sensors

#### `raw_temperature` -- Raw Temperature (Diagnostic)

- **Unit:** degrees C
- **Description:** Uncompensated temperature directly from the BME690. Includes sensor self-heating from the gas measurement heater, so it reads higher than the compensated `temperature` sensor. Useful for comparing raw vs compensated values or diagnosing temperature offset issues.

```yaml
sensor:
  - platform: bme68x_bsec3
    raw_temperature:
      name: "Raw Temperature"
```

#### `raw_humidity` -- Raw Humidity (Diagnostic)

- **Unit:** %
- **Description:** Uncompensated relative humidity directly from the BME690. Cross-influenced by the gas sensor heater. The compensated `humidity` sensor corrects for this effect.

```yaml
sensor:
  - platform: bme68x_bsec3
    raw_humidity:
      name: "Raw Humidity"
```

### Text Sensors

#### `iaq_accuracy` -- IAQ Accuracy (Text)

- **Description:** Human-readable calibration status string. Reports one of: `Stabilizing`, `Uncertain`, `Calibrating`, or `Calibrated`.

```yaml
text_sensor:
  - platform: bme68x_bsec3
    iaq_accuracy:
      name: "IAQ Accuracy"
```

#### `iaq_description` -- Air Quality Description

- **Description:** Human-readable air quality label derived from the IAQ value. Useful for dashboards, notifications, and automations.

| IAQ Range | Description |
|-----------|-------------|
| 0--50 | Excellent |
| 51--100 | Good |
| 101--150 | Lightly Polluted |
| 151--200 | Moderately Polluted |
| 201--250 | Heavily Polluted |
| 251--350 | Severely Polluted |
| 351--500 | Extremely Polluted |

```yaml
text_sensor:
  - platform: bme68x_bsec3
    iaq_description:
      name: "Air Quality"
```

## How It Works

1. **FreeRTOS task:** BSEC3 runs in a dedicated FreeRTOS task, keeping the main ESPHome loop free for API serving and other components.
2. **Sensor sampling:** The BME690 is read via I2C every 3 seconds in LP mode or every 300 seconds in ULP mode.
3. **Algorithm processing:** Raw temperature, humidity, pressure, and gas resistance readings are fed into the BSEC algorithm, which produces derived outputs (IAQ, CO2 equivalent, VOC equivalent, etc.).
4. **Calibration persistence:** The BSEC calibration state is saved to flash at the configured interval (default: every 6 hours). This state survives reboots, so the sensor does not need to fully recalibrate after a restart.
5. **Full calibration:** Reaching IAQ accuracy level 3 (fully calibrated) requires approximately 24--48 hours of continuous operation with exposure to both clean and polluted air.

## Differences from bme68x_bsec2

| Feature | bme68x_bsec2 | bme68x_bsec3 |
|---------|--------------|--------------|
| BSEC Version | 2.x | 3.3.0.0 |
| BME690 Support | Partial/broken | Full |
| BME688 Support | Yes | Yes |
| BME680 Support | Yes | No (use bme68x_bsec2) |
| Framework | Arduino + ESP-IDF | ESP-IDF only |
| Architecture | Main loop polling | FreeRTOS task |
| Power Efficiency | Baseline | BME690 uses ~50% less power |

If you have a **BME680**, continue using the built-in `bme68x_bsec2` component. This component does not support BME680.

## Known Limitations

- **ESP-IDF framework only** -- Arduino framework is not supported.
- **BSEC is proprietary** -- the library is downloaded from Bosch at build time (it is not in this repository), and compiled firmware that includes BSEC cannot be freely redistributed per Bosch's license terms.
- **First build needs network access** -- the BSEC library and BME69x SensorAPI are downloaded on the first compile, then cached.
- **Calibration takes time** -- IAQ accuracy 3 (fully calibrated) requires 24--48 hours of continuous operation.
- **TVOC equivalent** -- only available in LP sample rate mode, not ULP.
- **BME688 configuration limits** -- BME688 is limited to 3.3V / 28d configurations in BSEC3.

## Comparison to BME680

The BME690 is the latest in Bosch's environmental sensor line: BME680 -> BME688 -> BME690. Key improvements of BME690 over its predecessors:

- **50% lower power consumption** compared to BME688
- **Better condensation robustness** for use in humid environments
- **Pin-compatible** drop-in replacement for BME680/BME688
- **Requires BSEC3** -- BSEC2 produces incorrect values with BME690

## References

- [Bosch BME690 product page](https://www.bosch-sensortec.com/products/environmental-sensors/gas-sensors/bme690/)
- [BME690 SensorAPI (GitHub)](https://github.com/boschsensortec/BME690_SensorAPI)
- [BSEC software download](https://www.bosch-sensortec.com/software-tools/software/bme688-and-bme690-software/)
- [BME690 datasheet (PDF)](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme690-ds001.pdf)

## License

- **Component code** (everything in this repository): MIT -- see [`LICENSE`](LICENSE). This repository contains only the ESPHome component; no Bosch software is committed to it.
- **BSEC library** (`libalgobsec.a`, BSEC headers, config blobs): Proprietary Bosch Sensortec Software License Agreement. **Not** covered by the MIT license, and **not** distributed by this repository -- it is downloaded from Bosch Sensortec at build time. See the warning at the top of this file.
- **BME69x SensorAPI** (`bme69x.c`, `bme69x.h`, `bme69x_defs.h`): BSD-3-Clause (Bosch Sensortec). Also not committed to this repository -- downloaded from GitHub at build time.

See [`NOTICE`](NOTICE) for the full third-party attribution list.

### Why BSEC is downloaded at build time

ESPHome external components need the BSEC library available in a deterministic location during compilation. Rather than committing Bosch's proprietary binary to this repository, the build downloads it directly from Bosch Sensortec into the ESPHome data directory (`.esphome/bme68x_bsec3/`). This keeps the repository free of Bosch software while still giving users a one-step build. This repository does not attempt to relicense Bosch software.

### Verifying the BSEC download

The build downloads the official BSEC v3.3.0.0 release and verifies each extracted `libalgobsec.a` against a pinned SHA-256 checksum before linking it -- a mismatch fails the build. The pinned checksums correspond to the **unmodified** binaries as published by Bosch Sensortec:

| Architecture | File (inside the BSEC release zip) | SHA-256 |
|---|---|---|
| ESP32 | `release_bin/IAQ/bin/esp/esp32/libalgobsec.a` | `f4e3982b1499c3541cec1ce0bf8c15314d1441d6b8174193e7a3f9b52619b3e5` |
| ESP32-S2 | `release_bin/IAQ/bin/esp/esp32_s2/libalgobsec.a` | `0a64955209b0756c1032700d0176e243d52077726ccba512ab841c9c7ecb02d0` |
| ESP32-S3 | `release_bin/IAQ/bin/esp/esp32_s3/libalgobsec.a` | `11bd5b9494d59d0629218f6f00df795e12f5f9dde77046add83258231a09aec5` |
| ESP32-C2 / C3 / C6 | `release_bin/IAQ/bin/esp/esp32_c2c3/libalgobsec.a` | `c244365ae47bc3dd008264378b81856650b0bcbeacdbf3acc1ee4566d51d380b` |
