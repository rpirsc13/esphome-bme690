"""ESPHome component for BME688/BME690 air quality sensor via Bosch BSEC3.

This component does NOT bundle any Bosch software. At build time it downloads:

  * Bosch BSEC v3.3.0.0 (proprietary) — the precompiled ``libalgobsec.a``,
    its headers and config blobs, fetched directly from Bosch Sensortec.
    Downloading does not grant a license; the user must accept Bosch's
    Software License Agreement by setting ``accept_bosch_license: true``.
  * Bosch BME69x SensorAPI v1.1.0 (BSD-3-Clause) — the ``bme69x.*`` driver,
    fetched from the boschsensortec GitHub repository.

The downloaded BSEC binaries are verified against pinned SHA-256 checksums.
"""

import hashlib
import logging
import re
import zipfile
from pathlib import Path

from esphome import external_files
import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.const import (
    CONF_ID,
    CONF_MODEL,
    CONF_TEMPERATURE_OFFSET,
)
from esphome.core import coroutine_with_priority, CORE
from esphome.components import i2c

_LOGGER = logging.getLogger(__name__)

DOMAIN = "bme68x_bsec3"

CODEOWNERS = ["@sweitzja"]
DEPENDENCIES = ["i2c"]
AUTO_LOAD = ["sensor", "text_sensor"]

# --- Bosch BSEC v3.3.0.0 (proprietary) ----------------------------------------
# Downloaded at build time, never redistributed by this repository. The direct
# URL is the one published on Bosch Sensortec's software downloads page.
BSEC3_VERSION = "3.3.0.0"
BSEC3_URL = (
    "https://www.bosch-sensortec.com/media/boschsensortec/software_tools/"
    "software/bme_690/bsec_v3-3-0-0.zip"
)
# Path prefix inside the zip for the IAQ release (binaries, headers, configs).
BSEC3_ZIP_ROOT = "release_bin/IAQ/"
BSEC3_ZIP_WANTED = ("bin/esp/", "inc/", "config/bme688/", "config/bme690/")
# SHA-256 of the precompiled libalgobsec.a files inside the official zip. The
# build fails if an extracted binary does not match — this both verifies the
# download is intact and pins it to the exact, unmodified Bosch v3.3.0.0 release.
BSEC3_LIB_SHA256 = {
    "esp32": "f4e3982b1499c3541cec1ce0bf8c15314d1441d6b8174193e7a3f9b52619b3e5",
    "esp32_s2": "0a64955209b0756c1032700d0176e243d52077726ccba512ab841c9c7ecb02d0",
    "esp32_s3": "11bd5b9494d59d0629218f6f00df795e12f5f9dde77046add83258231a09aec5",
    "esp32_c2c3": "c244365ae47bc3dd008264378b81856650b0bcbeacdbf3acc1ee4566d51d380b",
}

# --- Bosch BME69x SensorAPI v1.1.0 (BSD-3-Clause) -----------------------------
# Downloaded into this component's directory so ESPHome auto-compiles bme69x.c.
BME69X_API_VERSION = "v1.1.0"
BME69X_API_BASE = (
    "https://raw.githubusercontent.com/boschsensortec/BME690_SensorAPI/"
    f"{BME69X_API_VERSION}"
)
BME69X_API_FILES = ("bme69x.c", "bme69x.h", "bme69x_defs.h")

CONF_SUPPLY_VOLTAGE = "supply_voltage"
CONF_SAMPLE_RATE = "sample_rate"
CONF_OPERATING_AGE = "operating_age"
CONF_STATE_SAVE_INTERVAL = "state_save_interval"
CONF_ACCEPT_BOSCH_LICENSE = "accept_bosch_license"
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


def _accept_bosch_license(value):
    """Require explicit acceptance of Bosch's BSEC license before downloading it."""
    if cv.boolean(value) is not True:
        raise cv.Invalid(
            "The BSEC algorithm library is proprietary Bosch Sensortec software. "
            "This component downloads it at build time but grants you no license "
            "to it. You must review and accept the Bosch Sensortec Software "
            "License Agreement at "
            "https://www.bosch-sensortec.com/software-tools/software/"
            "bme688-and-bme690-software/ — then set "
            f"'{CONF_ACCEPT_BOSCH_LICENSE}: true' to confirm acceptance."
        )
    return True


def _validate_model_options(config):
    """Validate that the model supports the chosen voltage/age combo."""
    model = config[CONF_MODEL]
    if model == "bme688":
        if config.get(CONF_SUPPLY_VOLTAGE) == "1.8V":
            raise cv.Invalid("BME688 BSEC3 configs are only available for 3.3V supply")
        if config.get(CONF_OPERATING_AGE) == "4d":
            raise cv.Invalid("BME688 BSEC3 configs are only available for 28d operating age")
    return config


def _bsec3_extract_dir() -> Path:
    """Cache directory holding the extracted BSEC3 release."""
    return external_files.compute_local_file_dir(DOMAIN) / f"bsec_v{BSEC3_VERSION}"


def _bsec3_lib_status(extract_dir: Path):
    """Check the extracted libalgobsec.a files.

    Returns (all_present, mismatch_arch) — mismatch_arch is the name of the
    first architecture whose checksum does not match, or None.
    """
    for arch, expected in BSEC3_LIB_SHA256.items():
        lib = extract_dir / "bin" / "esp" / arch / "libalgobsec.a"
        if not lib.is_file():
            return False, None
        if hashlib.sha256(lib.read_bytes()).hexdigest() != expected:
            return True, arch
    return True, None


def _extract_bsec3(zip_path: Path, extract_dir: Path):
    """Extract just the IAQ binaries, headers and config blobs from the zip."""
    with zipfile.ZipFile(zip_path) as zf:
        for info in zf.infolist():
            if info.is_dir() or not info.filename.startswith(BSEC3_ZIP_ROOT):
                continue
            rel = info.filename[len(BSEC3_ZIP_ROOT) :]
            if not rel.startswith(BSEC3_ZIP_WANTED):
                continue
            dest = extract_dir / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(zf.read(info))


def _download_dependencies(config):
    """Download the BSEC3 library and the BME69x SensorAPI at config time."""
    extract_dir = _bsec3_extract_dir()
    zip_path = extract_dir.with_suffix(".zip")

    libs_ok, mismatch = _bsec3_lib_status(extract_dir)
    headers_ok = (extract_dir / "inc" / "bsec_interface.h").is_file()
    if not libs_ok or not headers_ok:
        _LOGGER.info(
            "Downloading Bosch BSEC v%s (proprietary, ~6.5 MB) from %s",
            BSEC3_VERSION,
            BSEC3_URL,
        )
        external_files.download_content(BSEC3_URL, zip_path)
        _extract_bsec3(zip_path, extract_dir)
        zip_path.unlink(missing_ok=True)
        libs_ok, mismatch = _bsec3_lib_status(extract_dir)

    if mismatch:
        raise cv.Invalid(
            f"BSEC3 library checksum mismatch for '{mismatch}'. The downloaded "
            f"Bosch BSEC package does not match the expected, unmodified "
            f"v{BSEC3_VERSION} release. Delete '{extract_dir}' and rebuild."
        )
    if not libs_ok:
        raise cv.Invalid(
            f"BSEC3 libraries are missing after extraction in '{extract_dir}'. "
            f"Delete that directory and rebuild to re-download."
        )

    # Bosch BME69x SensorAPI (BSD-3-Clause) — placed directly in this
    # component's directory so ESPHome auto-compiles bme69x.c. The version is
    # pinned, so a file that is already present is already correct.
    component_dir = Path(__file__).parent
    for fname in BME69X_API_FILES:
        dest = component_dir / fname
        if not dest.is_file():
            _LOGGER.info(
                "Downloading Bosch BME69x SensorAPI %s (%s)",
                fname,
                BME69X_API_VERSION,
            )
            external_files.download_content(f"{BME69X_API_BASE}/{fname}", dest)

    return config


CONFIG_SCHEMA = cv.All(
    cv.Schema(
        {
            cv.GenerateID(): cv.declare_id(BME68xBSEC3Component),
            cv.GenerateID(CONF_RAW_DATA_ID): cv.declare_id(cg.uint8),
            cv.Required(CONF_MODEL): cv.one_of(*MODEL_OPTIONS, lower=True),
            cv.Required(CONF_ACCEPT_BOSCH_LICENSE): _accept_bosch_license,
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
    _download_dependencies,
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
    voltage_str = "33v"
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

    # BSEC3 is downloaded and extracted by _download_dependencies() at config
    # validation time; here we just point the build at the cached files.
    component_dir = Path(__file__).parent
    extract_dir = _bsec3_extract_dir()

    config_dir_name = f"{model}_iaq_{voltage_str}_{sample_str}_{age_str}"
    config_path = (
        extract_dir / "config" / model / config_dir_name / "bsec_iaq.c"
    )
    if not config_path.exists():
        raise cv.Invalid(
            f"BSEC3 config blob not found: {config_path}\n"
            f"Delete '{extract_dir}' and rebuild to re-download the BSEC3 release."
        )

    # Parse config blob and embed as progmem array
    config_bytes = _parse_config_blob(config_path)
    bsec3_arr = cg.progmem_array(config[CONF_RAW_DATA_ID], config_bytes)
    cg.add(var.set_bsec3_configuration(bsec3_arr, len(config_bytes)))

    # Build flags: include paths for the BSEC3 headers and this component
    # (the latter for the downloaded bme69x.h SensorAPI header).
    cg.add_build_flag(f"-I{extract_dir / 'inc'}")
    cg.add_build_flag(f"-I{component_dir}")

    # Link the arch-specific BSEC3 library
    arch = _get_bsec3_arch()
    lib_path = extract_dir / "bin" / "esp" / arch
    if not (lib_path / "libalgobsec.a").exists():
        raise cv.Invalid(
            f"BSEC3 library not found for architecture {arch}: {lib_path}\n"
            f"Delete '{extract_dir}' and rebuild to re-download the BSEC3 release."
        )
    cg.add_build_flag(f"-L{lib_path}")
    cg.add_build_flag("-lalgobsec")

    # Increase main task stack for API encryption + sensor publishing
    from esphome.components.esp32 import add_idf_sdkconfig_option

    add_idf_sdkconfig_option("CONFIG_ESP_MAIN_TASK_STACK_SIZE", 24576)
