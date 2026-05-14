"""ESPHome component for BME688/BME690 air quality sensor via Bosch BSEC3."""

import logging
import os
import re
from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import (
    CONF_ID,
    CONF_ADDRESS,
    CONF_MODEL,
    CONF_TEMPERATURE_OFFSET,
)
from esphome.core import coroutine_with_priority, CORE
from esphome.components import i2c

_LOGGER = logging.getLogger(__name__)

CODEOWNERS = ["@sweitzja"]
DEPENDENCIES = ["i2c"]
AUTO_LOAD = ["sensor", "text_sensor"]

CONF_SUPPLY_VOLTAGE = "supply_voltage"
CONF_SAMPLE_RATE = "sample_rate"
CONF_OPERATING_AGE = "operating_age"
CONF_STATE_SAVE_INTERVAL = "state_save_interval"
CONF_RAW_DATA_ID = "raw_data_id"

bme68x_bsec3_ns = cg.esphome_ns.namespace("bme68x_bsec3")
BME68xBSEC3Component = bme68x_bsec3_ns.class_(
    "BME68xBSEC3Component", cg.PollingComponent, i2c.I2CDevice
)

SampleRate = bme68x_bsec3_ns.enum("SampleRate")
SAMPLE_RATE_OPTIONS = {
    "LP": SampleRate.SAMPLE_RATE_LP,
    "ULP": SampleRate.SAMPLE_RATE_ULP,
}

SupplyVoltage = bme68x_bsec3_ns.enum("SupplyVoltage")
SUPPLY_VOLTAGE_OPTIONS = {
    "3.3V": SupplyVoltage.SUPPLY_VOLTAGE_3V3,
    "1.8V": SupplyVoltage.SUPPLY_VOLTAGE_1V8,
}

OperatingAge = bme68x_bsec3_ns.enum("OperatingAge")
OPERATING_AGE_OPTIONS = {
    "4d": OperatingAge.OPERATING_AGE_4D,
    "28d": OperatingAge.OPERATING_AGE_28D,
}

MODEL_OPTIONS = ["bme690", "bme688"]


def _validate_model_options(config):
    """Validate that the model supports the chosen voltage/age combo."""
    model = config[CONF_MODEL]
    if model == "bme688":
        if config.get(CONF_SUPPLY_VOLTAGE) == "1.8V":
            raise cv.Invalid("BME688 BSEC3 configs are only available for 3.3V supply")
        if config.get(CONF_OPERATING_AGE) == "4d":
            raise cv.Invalid("BME688 BSEC3 configs are only available for 28d operating age")
    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(BME68xBSEC3Component),
            cv.GenerateID(CONF_RAW_DATA_ID): cv.declare_id(cg.uint8),
            cv.Required(CONF_MODEL): cv.one_of(*MODEL_OPTIONS, lower=True),
            cv.Optional(CONF_SUPPLY_VOLTAGE, default="3.3V"): cv.enum(
                SUPPLY_VOLTAGE_OPTIONS
            ),
            cv.Optional(CONF_SAMPLE_RATE, default="LP"): cv.enum(
                SAMPLE_RATE_OPTIONS, upper=True
            ),
            cv.Optional(CONF_OPERATING_AGE, default="28d"): cv.enum(
                OPERATING_AGE_OPTIONS
            ),
            cv.Optional(CONF_TEMPERATURE_OFFSET, default=0.0): cv.float_,
            cv.Optional(
                CONF_STATE_SAVE_INTERVAL, default="6hours"
            ): cv.positive_time_period_minutes,
        }
    )
    .extend(i2c.i2c_device_schema(0x77))
    .extend(cv.polling_component_schema("3s")),
    _validate_model_options,
    cv.only_on_esp32,
)


def _get_bsec3_arch():
    """Determine the ESP32 variant for selecting the right libalgobsec.a."""
    variant = str(CORE.data.get("esp32", {}).get("variant", "ESP32")).upper()
    if variant == "ESP32S3":
        return "esp32_s3"
    elif variant == "ESP32S2":
        return "esp32_s2"
    elif variant in ("ESP32C3", "ESP32C2", "ESP32C6"):
        return "esp32_c2c3"
    else:
        return "esp32"


def _parse_config_blob(config_path):
    """Parse the BSEC config blob from a bsec_iaq.c file."""
    with open(config_path) as f:
        content = f.read()
    match = re.search(r"\{([^}]+)\}", content, re.DOTALL)
    if not match:
        raise cv.Invalid(f"Could not parse config blob from {config_path}")
    values = []
    for item in match.group(1).split(","):
        item = item.strip()
        if item:
            values.append(int(item, 0))
    return values


@coroutine_with_priority(60.0)
async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    await i2c.register_i2c_device(var, config)

    cg.add(var.set_sample_rate(config[CONF_SAMPLE_RATE]))
    cg.add(var.set_supply_voltage(config[CONF_SUPPLY_VOLTAGE]))
    cg.add(var.set_operating_age(config[CONF_OPERATING_AGE]))
    cg.add(var.set_temperature_offset(config[CONF_TEMPERATURE_OFFSET]))
    cg.add(
        var.set_state_save_interval(
            config[CONF_STATE_SAVE_INTERVAL].total_milliseconds
        )
    )

    # Select the right config blob based on model/voltage/sample_rate/age
    model = config[CONF_MODEL]
    voltage_str = "33v" if config[CONF_SUPPLY_VOLTAGE] == SUPPLY_VOLTAGE_OPTIONS["3.3V"] else "18v"
    # Map enum back to string
    for k, v in SUPPLY_VOLTAGE_OPTIONS.items():
        if v == config[CONF_SUPPLY_VOLTAGE]:
            voltage_str = "33v" if k == "3.3V" else "18v"
            break
    for k, v in SAMPLE_RATE_OPTIONS.items():
        if v == config[CONF_SAMPLE_RATE]:
            sample_str = "3s" if k == "LP" else "300s"
            break
    for k, v in OPERATING_AGE_OPTIONS.items():
        if v == config[CONF_OPERATING_AGE]:
            age_str = k
            break

    component_dir = Path(__file__).parent
    config_dir_name = f"{model}_iaq_{voltage_str}_{sample_str}_{age_str}"
    config_path = (
        component_dir
        / "bosch"
        / "bsec3"
        / "config"
        / model
        / config_dir_name
        / "bsec_iaq.c"
    )

    if not config_path.exists():
        raise cv.Invalid(
            f"BSEC3 config blob not found: {config_path}\n"
            f"Ensure the BSEC3 library is properly installed."
        )

    # Parse config blob and embed as progmem array
    config_bytes = _parse_config_blob(config_path)
    bsec3_arr = cg.progmem_array(config[CONF_RAW_DATA_ID], config_bytes)
    cg.add(var.set_bsec3_configuration(bsec3_arr, len(config_bytes)))

    # Build flags: include paths and FPU support
    cg.add_build_flag(f"-I{component_dir / 'bosch' / 'bsec3' / 'inc'}")
    cg.add_build_flag(f"-I{component_dir}")
    cg.add_build_flag("-DBME69X_USE_FPU")

    # Link the arch-specific BSEC3 library
    arch = _get_bsec3_arch()
    lib_path = component_dir / "bosch" / "bsec3" / "lib" / arch
    if not (lib_path / "libalgobsec.a").exists():
        raise cv.Invalid(
            f"BSEC3 library not found for architecture {arch}: {lib_path}\n"
            f"Ensure libalgobsec.a is present."
        )
    cg.add_build_flag(f"-L{lib_path}")
    cg.add_build_flag("-lalgobsec")

    # Increase main task stack for API encryption + sensor publishing
    from esphome.components.esp32 import add_idf_sdkconfig_option
    add_idf_sdkconfig_option("CONFIG_ESP_MAIN_TASK_STACK_SIZE", 16384)
