"""Text sensor platform for BME68x BSEC3."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import text_sensor
from esphome.const import ENTITY_CATEGORY_DIAGNOSTIC
from . import BME68xBSEC3Component

CONF_BME68X_BSEC3_ID = "bme68x_bsec3_id"
CONF_IAQ_ACCURACY = "iaq_accuracy"

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(CONF_BME68X_BSEC3_ID): cv.use_id(BME68xBSEC3Component),
        cv.Optional(CONF_IAQ_ACCURACY): text_sensor.text_sensor_schema(
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
            icon="mdi:checkbox-marked-circle-outline",
        ),
    }
)


async def to_code(config):
    parent = await cg.get_variable(config[CONF_BME68X_BSEC3_ID])

    if CONF_IAQ_ACCURACY in config:
        sens = await text_sensor.new_text_sensor(config[CONF_IAQ_ACCURACY])
        cg.add(parent.set_iaq_accuracy_text_sensor(sens))
