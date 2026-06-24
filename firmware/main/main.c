/************************************************************************
 * Temperature/Humidity/Power Monitor
 *
 * for ESP32
 * by Jim Shortz
 *
 * This system remotely monitors a dehumidifier.  It reports
 * temperature, humidity, and power consumption via MQTT
 * at regular intervals.
 *
 * This version uses the ESP-IDF SDK instead of the Arduino layer.
 ************************************************************************/

#include <dht.h>
#include <driver/gpio.h>
#include <driver/uart.h>
#include <esp_event.h>
#include <esp_log.h>
#include <esp_system.h>
#include <esp_wifi.h>
#include <freertos/FreeRTOS.h>
#include <freertos/task.h>
#include <mqtt_client.h>
#include <nvs_flash.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
#include <sys/param.h>

#include "adc.h"
#include "config.h"

/* Feature flags - disable for debugging */
#define USE_NETWORK 1
#define USE_CURRENT 1
#define USE_DHT22 1

/* Hard-coded constants */
const int power_led = GPIO_NUM_13;
const int dht22_pin = GPIO_NUM_32;
const value_t line_voltage = 120;
const value_t power_factor = 0.96;
const int reporting_period = 15000;

esp_mqtt_client_handle_t mqtt_client = NULL;
static const char *TAG = "main";

/************************************************************************
 * Forward declarations
 ************************************************************************/
static void wifi_event_handler(void *, esp_event_base_t, int32_t, void *);
static void mqtt_event_handler(void *, esp_event_base_t, int32_t, void *);
static void sensor_loop(void *params);

/************************************************************************
 * Main function.  Initializes hardware, networking, and runs the
 * measurement loop.  Does not exit.
 ************************************************************************/
void app_main(void) {
  esp_err_t ret;

  ESP_LOGI(TAG, "Humidity Monitor Starting...");
  ESP_LOGI(TAG, "Temperature/Humidity/Power Sensor v3.0 (C) 2021,2026 - by Jim Shortz");

  ret = uart_driver_install(CONFIG_UART, 256, 0, 0, NULL, 0);
  ESP_ERROR_CHECK(ret);

  /* Set up non volatile storage */
  ret = nvs_flash_init();
  if (ret == ESP_ERR_NVS_NO_FREE_PAGES ||
      ret == ESP_ERR_NVS_NEW_VERSION_FOUND) {
    ESP_ERROR_CHECK(nvs_flash_erase());
    ret = nvs_flash_init();
  }
  ESP_ERROR_CHECK(ret);

  /* Read configuration from NVS */
  if (!init_config() || prompt_config_edit()) {
    edit_config();
  }

  /* Set up hardware */
#if USE_CURRENT
  ESP_ERROR_CHECK(adc_init());
#endif

#if USE_NETWORK
  /* Set up networking */
  ESP_ERROR_CHECK(esp_netif_init());
  ESP_ERROR_CHECK(esp_event_loop_create_default());
  esp_netif_create_default_wifi_sta();

  wifi_init_config_t cfg = WIFI_INIT_CONFIG_DEFAULT();
  ESP_ERROR_CHECK(esp_wifi_init(&cfg));

  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      WIFI_EVENT, ESP_EVENT_ANY_ID, &wifi_event_handler, NULL, NULL));

  ESP_ERROR_CHECK(esp_event_handler_instance_register(
      IP_EVENT, IP_EVENT_STA_GOT_IP, &wifi_event_handler, NULL, NULL));

  ESP_ERROR_CHECK(esp_wifi_set_mode(WIFI_MODE_STA));
  ESP_ERROR_CHECK(esp_wifi_set_config(WIFI_IF_STA, &wifi_config));
  ESP_ERROR_CHECK(esp_wifi_start());

  /* Initialize MQTT */
  mqtt_client = esp_mqtt_client_init(&mqtt_cfg);
  esp_mqtt_client_register_event(mqtt_client, ESP_EVENT_ANY_ID,
                                 mqtt_event_handler, NULL);
  esp_mqtt_client_start(mqtt_client);
#endif

  sensor_loop(NULL);
}

/************************************************************************
 * Helper to publish a single metric.  Handles formatting of topic and
 * payload.
 ************************************************************************/
void publish_metric(const char *topic, const char *fmt_string, value_t val) {

  char full_topic[128];
  char payload[16];

  /* Build topic name from root */
  strcpy(full_topic, topic_root);
  strcat(full_topic, topic);
  snprintf(payload, sizeof(payload), fmt_string, val);

  int msg_id =
      esp_mqtt_client_publish(mqtt_client, full_topic, payload, 0, 1, 0);
  if (msg_id < 0) {
    ESP_LOGW(TAG, "Failed to publish %s=%s", topic, payload);
  }
}

/************************************************************************
 * Perform readings and publish them to MQTT.  Silently ignores MQTT
 * publish failures.
 ************************************************************************/
static void sensor_loop(void *params) {
  TickType_t last_wake = xTaskGetTickCount();

  while (1) {
    esp_err_t ret;

#if USE_CURRENT
    value_t volts;
    ret = adc_rms_read(&volts);
    if (ret == ESP_OK) {
      value_t current = volts * amps_per_volt;
      value_t power = current * line_voltage * power_factor;

      ESP_LOGI(TAG, "Read power %.1f watts", power);
      publish_metric("power", "%.0f", power);
    } else {
      ESP_LOGE(TAG, "Error %d reading adc: %s", ret, esp_err_to_name(ret));
    }
#endif

#if USE_DHT22
    int16_t humid, temp_c;
    value_t temp_f, humid_pct;

    ret = dht_read_data(DHT_TYPE_DHT22, dht22_pin, &humid, &temp_c);
    temp_f = (temp_c * 9.0 / 5.0 / 10.0) + 32;
    humid_pct = humid / 10.0;

    if (ret == ESP_OK) {
      ESP_LOGI(TAG, "temp=%.1f humidity=%.1f", temp_f, humid_pct);
      publish_metric("indoor_temp", "%.1f", temp_f);
      publish_metric("indoor_humid", "%.1f", humid_pct);
    } else {
      ESP_LOGE(TAG, "Error %d reading dht22: %s", ret, esp_err_to_name(ret));
    }
#endif

    /* Sleep until the next reporting period */
    vTaskDelayUntil(&last_wake, pdMS_TO_TICKS(reporting_period));
  }
}

static void wifi_event_handler(void *arg, esp_event_base_t event_base,
                               int32_t event_id, void *event_data) {
  if (event_base == WIFI_EVENT && event_id == WIFI_EVENT_STA_START) {
    ESP_LOGI(TAG, "Connecting to WiFi...");
    esp_wifi_connect();
  } else if (event_base == WIFI_EVENT &&
             event_id == WIFI_EVENT_STA_DISCONNECTED) {
    ESP_LOGW(TAG, "WiFi lost. Retrying...");
    esp_wifi_connect();
  } else if (event_base == IP_EVENT && event_id == IP_EVENT_STA_GOT_IP) {
    ip_event_got_ip_t *event = (ip_event_got_ip_t *)event_data;
    ESP_LOGI(TAG, "Got IP: " IPSTR, IP2STR(&event->ip_info.ip));
  }
}

static void mqtt_event_handler(void *handler_args, esp_event_base_t base,
                               int32_t event_id, void *event_data) {
  switch ((esp_mqtt_event_id_t)event_id) {
  case MQTT_EVENT_CONNECTED:
    ESP_LOGI(TAG, "MQTT Connected to %s", mqtt_url);
    break;

  case MQTT_EVENT_DISCONNECTED:
    ESP_LOGW(TAG, "MQTT Disconnected!");
    break;

  case MQTT_EVENT_ERROR:
    ESP_LOGE(TAG, "MQTT Error occurred");
    break;

  default:
    break;
  }
}
