"""Sensor platform for BME68x BSEC3."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor
from esphome.const import (
    CONF_ID,
    CONF_HUMIDITY,
    CONF_PRESSURE,
    CONF_TEMPERATURE,
    CONF_GAS_RESISTANCE,
    DEVICE_CLASS_HUMIDITY,
    DEVICE_CLASS_PRESSURE,
    DEVICE_CLASS_TEMPERATURE,
    DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS_PARTS,
    DEVICE_CLASS_CARBON_DIOXIDE,
    ENTITY_CATEGORY_DIAGNOSTIC,
    ICON_GAS_CYLINDER,
    ICON_THERMOMETER,
    STATE_CLASS_MEASUREMENT,
    UNIT_CELSIUS,
    UNIT_HECTOPASCAL,
    UNIT_OHM,
    UNIT_PARTS_PER_MILLION,
    UNIT_PERCENT,
)
from . import BME68xBSEC3Component, bme68x_bsec3_ns

CONF_BME68X_BSEC3_ID = "bme68x_bsec3_id"
CONF_IAQ = "iaq"
CONF_IAQ_ACCURACY = "iaq_accuracy"
CONF_IAQ_STATIC = "iaq_static"
CONF_CO2_EQUIVALENT = "co2_equivalent"
CONF_BREATH_VOC_EQUIVALENT = "breath_voc_equivalent"
CONF_GAS_PERCENTAGE = "gas_percentage"
CONF_COMPENSATED_TEMPERATURE = "compensated_temperature"
CONF_COMPENSATED_HUMIDITY = "compensated_humidity"

UNIT_IAQ = "IAQ"
ICON_ACCURACY = "mdi:checkbox-marked-circle-outline"
ICON_TEST_TUBE = "mdi:test-tube"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_BME68X_BSEC3_ID): cv.use_id(BME68xBSEC3Component),
        cv.Optional(CONF_TEMPERATURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_HUMIDITY): sensor.sensor_schema(
            unit_of_measurement=UNIT_PERCENT,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_HUMIDITY,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_PRESSURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_HECTOPASCAL,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_PRESSURE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_GAS_RESISTANCE): sensor.sensor_schema(
            unit_of_measurement=UNIT_OHM,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
            icon=ICON_GAS_CYLINDER,
        ),
        cv.Optional(CONF_IAQ): sensor.sensor_schema(
            unit_of_measurement=UNIT_IAQ,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
            icon="mdi:air-filter",
        ),
        cv.Optional(CONF_IAQ_ACCURACY): sensor.sensor_schema(
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            icon=ICON_ACCURACY,
        ),
        cv.Optional(CONF_IAQ_STATIC): sensor.sensor_schema(
            unit_of_measurement=UNIT_IAQ,
            accuracy_decimals=0,
            state_class=STATE_CLASS_MEASUREMENT,
            icon="mdi:air-filter",
        ),
        cv.Optional(CONF_CO2_EQUIVALENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_PARTS_PER_MILLION,
            accuracy_decimals=0,
            device_class=DEVICE_CLASS_CARBON_DIOXIDE,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_BREATH_VOC_EQUIVALENT): sensor.sensor_schema(
            unit_of_measurement=UNIT_PARTS_PER_MILLION,
            accuracy_decimals=2,
            device_class=DEVICE_CLASS_VOLATILE_ORGANIC_COMPOUNDS_PARTS,
            state_class=STATE_CLASS_MEASUREMENT,
        ),
        cv.Optional(CONF_GAS_PERCENTAGE): sensor.sensor_schema(
            unit_of_measurement=UNIT_PERCENT,
            accuracy_decimals=1,
            state_class=STATE_CLASS_MEASUREMENT,
            icon=ICON_TEST_TUBE,
        ),
        cv.Optional(CONF_COMPENSATED_TEMPERATURE): sensor.sensor_schema(
            unit_of_measurement=UNIT_CELSIUS,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_TEMPERATURE,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
        cv.Optional(CONF_COMPENSATED_HUMIDITY): sensor.sensor_schema(
            unit_of_measurement=UNIT_PERCENT,
            accuracy_decimals=1,
            device_class=DEVICE_CLASS_HUMIDITY,
            state_class=STATE_CLASS_MEASUREMENT,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ),
    }
)


async def to_code(config):
    parent = await cg.get_variable(config[CONF_BME68X_BSEC3_ID])

    for conf_key, setter in [
        (CONF_TEMPERATURE, parent.set_temperature_sensor),
        (CONF_HUMIDITY, parent.set_humidity_sensor),
        (CONF_PRESSURE, parent.set_pressure_sensor),
        (CONF_GAS_RESISTANCE, parent.set_gas_resistance_sensor),
        (CONF_IAQ, parent.set_iaq_sensor),
        (CONF_IAQ_ACCURACY, parent.set_iaq_accuracy_sensor),
        (CONF_IAQ_STATIC, parent.set_static_iaq_sensor),
        (CONF_CO2_EQUIVALENT, parent.set_co2_equivalent_sensor),
        (CONF_BREATH_VOC_EQUIVALENT, parent.set_breath_voc_equivalent_sensor),
        (CONF_GAS_PERCENTAGE, parent.set_gas_percentage_sensor),
        (CONF_COMPENSATED_TEMPERATURE, parent.set_compensated_temperature_sensor),
        (CONF_COMPENSATED_HUMIDITY, parent.set_compensated_humidity_sensor),
    ]:
        if conf_key in config:
            sens = await sensor.new_sensor(config[conf_key])
            cg.add(setter(sens))
