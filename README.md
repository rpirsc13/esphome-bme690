# esphome-bme690

ESPHome external component for **BME690** and **BME688** air quality sensors using Bosch's BSEC v3.3.0.0 algorithm library.

Drop-in sensor platform providing Indoor Air Quality (IAQ), estimated CO2, VOC, temperature, humidity, and barometric pressure. Supports ESP32, ESP32-S2, ESP32-S3, ESP32-C2, ESP32-C3, and ESP32-C6. **ESP-IDF framework required.**

---

> **WARNING: BSEC License Agreement Required**
>
> This component includes the **Bosch BSEC v3.3.0.0 precompiled library** (`libalgobsec.a`), which is **proprietary software** owned by Bosch Sensortec GmbH. By using this component, you agree to the **Bosch Sensortec Software License Agreement**.
>
> **You must accept the license terms at:**
> https://www.bosch-sensortec.com/en/software-tools/software/bme688-and-bme690-software/
>
> The precompiled binary is included in this repository for convenience only. Its use, copying, and distribution are governed entirely by Bosch's terms. **Firmware binaries that include BSEC cannot be redistributed** per the Bosch license.

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
  model: bme690            # bme690 or bme688
  address: 0x77            # 0x77 (default) or 0x76
  supply_voltage: 3.3V     # 3.3V or 1.8V
  sample_rate: LP           # LP (3s) or ULP (300s)
  operating_age: 28d        # 4d or 28d
  temperature_offset: 0     # Heat compensation offset (°C)
  state_save_interval: 6h   # BSEC calibration save interval
```

| Option | Default | Description |
|--------|---------|-------------|
| `model` | `bme690` | Sensor model: `bme690` or `bme688` |
| `address` | `0x77` | I2C address: `0x77` or `0x76` |
| `supply_voltage` | `3.3V` | Sensor supply voltage: `3.3V` or `1.8V` |
| `sample_rate` | `LP` | `LP` = Low Power (3s cycle), `ULP` = Ultra Low Power (300s cycle) |
| `operating_age` | `28d` | Algorithm training period: `4d` or `28d` |
| `temperature_offset` | `0` | Compensation for self-heating, in degrees Celsius |
| `state_save_interval` | `6h` | How often BSEC calibration state is saved to flash |

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

#### `compensated_temperature` -- Compensated Temperature (Diagnostic)

- **Unit:** degrees C
- **Description:** Same measurement as `temperature`, categorized as a diagnostic entity in Home Assistant. Useful if you want temperature in the diagnostics panel rather than as a primary sensor.

```yaml
sensor:
  - platform: bme68x_bsec3
    compensated_temperature:
      name: "Compensated Temperature"
```

#### `compensated_humidity` -- Compensated Humidity (Diagnostic)

- **Unit:** %
- **Description:** Same measurement as `humidity`, categorized as a diagnostic entity in Home Assistant.

```yaml
sensor:
  - platform: bme68x_bsec3
    compensated_humidity:
      name: "Compensated Humidity"
```

### Text Sensor

#### `iaq_accuracy` -- IAQ Accuracy (Text)

- **Description:** Human-readable calibration status string. Reports one of: `Stabilizing`, `Uncertain`, `Calibrating`, or `Calibrated`.

```yaml
text_sensor:
  - platform: bme68x_bsec3
    iaq_accuracy:
      name: "IAQ Accuracy"
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
- **BSEC is proprietary** -- compiled firmware that includes BSEC cannot be freely redistributed per Bosch's license terms.
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

- [Bosch BME690 product page](https://www.bosch-sensortec.com/en/products/environmental-sensors/gas-sensors/bme690)
- [BME690 SensorAPI (GitHub)](https://github.com/boschsensortec/BME690_SensorAPI)
- [BSEC software download](https://www.bosch-sensortec.com/en/software-tools/software/bme688-and-bme690-software)
- [BME690 datasheet (PDF)](https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme690-ds001-00.pdf)

## License

- **Component code** (this repository, excluding BSEC): MIT
- **BSEC library** (`libalgobsec.a`): Proprietary Bosch Sensortec license -- see [disclaimer](#esphome-bme690) above.
- **BME69x SensorAPI**: BSD-3-Clause (Bosch Sensortec)
