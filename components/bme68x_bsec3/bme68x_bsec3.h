#pragma once

#include "esphome/core/component.h"
#include "esphome/components/i2c/i2c.h"

#ifdef USE_SENSOR
#include "esphome/components/sensor/sensor.h"
#endif
#ifdef USE_TEXT_SENSOR
#include "esphome/components/text_sensor/text_sensor.h"
#endif

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"

extern "C" {
#include "bme69x.h"
#include "bsec_interface.h"
#include "bsec_datatypes.h"
}

namespace esphome {
namespace bme68x_bsec3 {

enum SampleRate : uint8_t {
  SAMPLE_RATE_LP,   // 3s
  SAMPLE_RATE_ULP,  // 300s
};

enum SupplyVoltage : uint8_t {
  SUPPLY_VOLTAGE_3V3,
  SUPPLY_VOLTAGE_1V8,
};

enum OperatingAge : uint8_t {
  OPERATING_AGE_4D,
  OPERATING_AGE_28D,
};

class BME68xBSEC3Component : public PollingComponent, public i2c::I2CDevice {
 public:
  void setup() override;
  void loop() override;
  void update() override;
  void dump_config() override;
  float get_setup_priority() const override;

  // Config setters
  void set_sample_rate(SampleRate rate) { this->sample_rate_ = rate; }
  void set_supply_voltage(SupplyVoltage voltage) { this->supply_voltage_ = voltage; }
  void set_operating_age(OperatingAge age) { this->operating_age_ = age; }
  void set_temperature_offset(float offset) { this->temperature_offset_ = offset; }
  void set_state_save_interval(uint32_t ms) { this->state_save_interval_ms_ = ms; }
  void set_bsec3_configuration(const uint8_t *data, uint32_t length) {
    this->bsec3_config_data_ = data;
    this->bsec3_config_length_ = length;
  }

  // Sensor setters
#ifdef USE_SENSOR
  void set_temperature_sensor(sensor::Sensor *s) { this->temperature_sensor_ = s; }
  void set_humidity_sensor(sensor::Sensor *s) { this->humidity_sensor_ = s; }
  void set_pressure_sensor(sensor::Sensor *s) { this->pressure_sensor_ = s; }
  void set_gas_resistance_sensor(sensor::Sensor *s) { this->gas_resistance_sensor_ = s; }
  void set_iaq_sensor(sensor::Sensor *s) { this->iaq_sensor_ = s; }
  void set_iaq_accuracy_sensor(sensor::Sensor *s) { this->iaq_accuracy_sensor_ = s; }
  void set_static_iaq_sensor(sensor::Sensor *s) { this->static_iaq_sensor_ = s; }
  void set_co2_equivalent_sensor(sensor::Sensor *s) { this->co2_equivalent_sensor_ = s; }
  void set_breath_voc_equivalent_sensor(sensor::Sensor *s) { this->breath_voc_equivalent_sensor_ = s; }
  void set_gas_percentage_sensor(sensor::Sensor *s) { this->gas_percentage_sensor_ = s; }
  void set_tvoc_equivalent_sensor(sensor::Sensor *s) { this->tvoc_equivalent_sensor_ = s; }
  void set_compensated_temperature_sensor(sensor::Sensor *s) { this->compensated_temperature_sensor_ = s; }
  void set_compensated_humidity_sensor(sensor::Sensor *s) { this->compensated_humidity_sensor_ = s; }
#endif
#ifdef USE_TEXT_SENSOR
  void set_iaq_accuracy_text_sensor(text_sensor::TextSensor *s) { this->iaq_accuracy_text_sensor_ = s; }
#endif

 protected:
  // FreeRTOS task
  static void bsec_task_(void *param);
  void bsec_task_main_();

  // BSEC helpers
  void init_bsec_();
  void subscribe_outputs_();
  void process_sensor_data_(int64_t time_ns, struct bme69x_data *data, uint32_t process_data);
  void save_state_();
  void load_state_();

  // BME69x I2C callbacks
  static BME69X_INTF_RET_TYPE i2c_read_(uint8_t reg_addr, uint8_t *data, uint32_t len, void *intf_ptr);
  static BME69X_INTF_RET_TYPE i2c_write_(uint8_t reg_addr, const uint8_t *data, uint32_t len, void *intf_ptr);
  static void delay_us_(uint32_t period, void *intf_ptr);

  // BSEC3 instance memory (dynamically allocated via bsec_get_instance_size())
  uint8_t *bsec_instance_{nullptr};

  // BME69x device
  struct bme69x_dev bme69x_dev_{};
  struct bme69x_conf bme69x_conf_{};
  struct bme69x_heatr_conf bme69x_heatr_conf_{};
  uint8_t last_op_mode_{BME69X_SLEEP_MODE};
  uint8_t current_op_mode_{BME69X_SLEEP_MODE};

  // Shared output struct (protected by mutex)
  struct SensorData {
    float temperature{0};
    float humidity{0};
    float pressure{0};
    float gas_resistance{0};
    float iaq{0};
    uint8_t iaq_accuracy{0};
    float static_iaq{0};
    float co2_equivalent{0};
    float breath_voc_equivalent{0};
    float gas_percentage{0};
    float tvoc_equivalent{0};
    float compensated_temperature{0};
    float compensated_humidity{0};
    bool valid{false};
  };
  SensorData sensor_data_{};
  volatile bool data_available_{false};
  SemaphoreHandle_t data_mutex_{nullptr};
  TaskHandle_t task_handle_{nullptr};

  // Config
  const uint8_t *bsec3_config_data_{nullptr};
  uint32_t bsec3_config_length_{0};
  float temperature_offset_{0};
  SampleRate sample_rate_{SAMPLE_RATE_LP};
  SupplyVoltage supply_voltage_{SUPPLY_VOLTAGE_3V3};
  OperatingAge operating_age_{OPERATING_AGE_28D};

  // State persistence
  uint32_t state_save_interval_ms_{21600000};  // 6 hours
  uint32_t last_state_save_ms_{0};


  // Sensors
#ifdef USE_SENSOR
  sensor::Sensor *temperature_sensor_{nullptr};
  sensor::Sensor *humidity_sensor_{nullptr};
  sensor::Sensor *pressure_sensor_{nullptr};
  sensor::Sensor *gas_resistance_sensor_{nullptr};
  sensor::Sensor *iaq_sensor_{nullptr};
  sensor::Sensor *iaq_accuracy_sensor_{nullptr};
  sensor::Sensor *static_iaq_sensor_{nullptr};
  sensor::Sensor *co2_equivalent_sensor_{nullptr};
  sensor::Sensor *breath_voc_equivalent_sensor_{nullptr};
  sensor::Sensor *gas_percentage_sensor_{nullptr};
  sensor::Sensor *tvoc_equivalent_sensor_{nullptr};
  sensor::Sensor *compensated_temperature_sensor_{nullptr};
  sensor::Sensor *compensated_humidity_sensor_{nullptr};
#endif
#ifdef USE_TEXT_SENSOR
  text_sensor::TextSensor *iaq_accuracy_text_sensor_{nullptr};
#endif
};

}  // namespace bme68x_bsec3
}  // namespace esphome
