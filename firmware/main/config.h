#pragma once

#include <esp_wifi_types.h>
#include <mqtt_client.h>

/* UART to use for configuration user interface */
#define CONFIG_UART CONFIG_ESP_CONSOLE_UART_NUM

/* Standard type for data values.   Float is sufficient accuracy for this */
typedef float value_t;

/* Prefix to be prepended to all topic names */
extern char topic_root[256];

/* WiFi credentials */
extern wifi_config_t wifi_config;

/* MQTT connection info */
extern esp_mqtt_client_config_t mqtt_cfg;
extern char mqtt_url[128];
extern char mqtt_user[32];
extern char mqtt_pass[32];

/* Current rating of sensing transformer */
extern value_t amps_per_volt;

/* Configuration management functions */
int init_config();
int prompt_config_edit();
void edit_config();
