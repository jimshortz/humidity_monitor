/************************************************************************
 * Configuration management for kiln controller
 *
 * This module stores global configuration settings.  It handles
 * loading/saving them from non-volatile storage and allowing the user
 * to edit them via the serial port.
 ************************************************************************/
#include "config.h"

#include <ctype.h>
#include <driver/uart.h>
#include <esp_log.h>
#include <nvs.h>
#include <nvs_flash.h>
#include <stdio.h>

/* Possible types for a configurable item */
typedef enum {
  CONFIG_STR,   /* String buffer */
  CONFIG_VALUE, /* value_t */
} config_value_t;

/* Defines a configurable item */
typedef struct {
  const char *key;
  const char *desc;
  config_value_t type;
  void *value;
  size_t size;
} config_item_t;

/* Table of configurable items */
const config_item_t items[] = {
    {"wifi_ssid", "WiFi network name", CONFIG_STR, wifi_config.sta.ssid,
     sizeof(wifi_config.sta.ssid)},
    {"wifi_pass", "WiFi password", CONFIG_STR, wifi_config.sta.password,
     sizeof(wifi_config.sta.password)},
    {"mqtt_url", "MQTT URL", CONFIG_STR, mqtt_url, sizeof(mqtt_url)},
    {"mqtt_user", "MQTT Username", CONFIG_STR, mqtt_user, sizeof(mqtt_user)},
    {"mqtt_pass", "MQTT Password", CONFIG_STR, mqtt_pass, sizeof(mqtt_pass)},
    {"topic_root", "Topic prefix", CONFIG_STR, topic_root, sizeof(topic_root)},
    {"amps_per_volt", "Current sensor amps per volt", CONFIG_VALUE,
     &amps_per_volt, sizeof(amps_per_volt)},
};

/* Prefix appended to all topic names */
char topic_root[256] = "kiln/";

/* Wifi configuration (stored in the ESP structure */
wifi_config_t wifi_config;

/* MQTT strings - we have to store this in our own buffers */
char mqtt_url[128];
char mqtt_user[32];
char mqtt_pass[32];

/* Which are referenced in the ESP structure */
esp_mqtt_client_config_t mqtt_cfg = {
    .broker.address.uri = mqtt_url,
    .broker.address.port = 1883,
    .credentials.username = mqtt_user,
    .credentials.authentication.password = mqtt_pass,
};

/* Current rating of sensing transformer.  1V = 60A */
value_t amps_per_volt = 20.0;

static const char *TAG = "config";

/* Line editing buffer - reused in several places */
static char buf[64];

/* Forward declarations for functions in this file */
char read_char();
int read_line(char *, size_t);
void edit_item(const config_item_t *);
void print_settings();
void write_char(char);

/************************************************************************
 * Reads the configuration from NVS into memory
 *
 * Returns 0 if valid NVS configuration not found.  Some items may
 * be valid.
 ************************************************************************/
int init_config() {
  nvs_handle_t h;
  esp_err_t ret;
  int success = 1;
  const config_item_t *item = items;

  ret = nvs_open("config", NVS_READONLY, &h);
  if (ret != ESP_OK) {
    return 0;
  }

  while (item < items + sizeof(items) / sizeof(config_item_t)) {
    size_t s = item->size;

    ret = nvs_get_blob(h, item->key, item->value, &s);
    if (ret != ESP_OK) {
      ESP_LOGW(TAG, "Error reading key %s: %s", item->key,
               esp_err_to_name(ret));
      success = 0;
    }

    item++;
  }

  nvs_close(h);
  return success;
}

/************************************************************************
 * Writes and commits settings back to NVS.  Returns 1 if successful.
 ************************************************************************/
int save_config() {
  nvs_handle_t h;
  esp_err_t ret;
  int success = 1;
  const config_item_t *item = items;

  ret = nvs_open("config", NVS_READWRITE, &h);
  if (ret != ESP_OK) {
    ESP_LOGE(TAG, "Error opening NVS: %s", esp_err_to_name(ret));
    return 0;
  }

  while (item < items + (sizeof(items) / sizeof(config_item_t))) {
    size_t s = item->size;

    ret = nvs_set_blob(h, item->key, item->value, s);
    if (ret != ESP_OK) {
      ESP_LOGW(TAG, "Error writing key %s: %s", item->key,
               esp_err_to_name(ret));
      success = 0;
    }

    item++;
  }

  ret = nvs_commit(h);

  if (ret != ESP_OK) {
    ESP_LOGW(TAG, "Error committing changes: %s", esp_err_to_name(ret));
    success = 0;
  }

  nvs_close(h);

  return success;
}

/************************************************************************
 * Gives the user 10 seconds to edit the config.
 ************************************************************************/
int prompt_config_edit() {
  printf("Press C to configure...\n");
  return tolower(read_char()) == 'c';
}

/************************************************************************
 * Gives the user a menu for editing the configuration items.
 ************************************************************************/
void edit_config() {
  int choice;

  for (;;) {
    print_settings();

    if (read_line(buf, sizeof(buf))) {
      choice = atoi(buf);
      if (choice == 0 && buf[0] == '0') {
        printf("Saving configuration...\n");
        if (save_config()) {
          break;
        }
      } else if (choice > 0 &&
                 choice <= sizeof(items) / sizeof(config_item_t)) {
        edit_item(&items[choice - 1]);
      }
    } else {
      printf("Invalid item number\n");
    }
  }
}

/************************************************************************
 * Displays current setting values to the user.
 ************************************************************************/
void print_settings() {
  printf("Current settings:\n");
  const config_item_t *item = items;
  int i = 1;

  while (item < items + (sizeof(items) / sizeof(config_item_t))) {
    switch (item->type) {
    case CONFIG_STR:
      printf("%d. %s = %s\n", i, item->desc, (char *)item->value);
      break;
    case CONFIG_VALUE:
      printf("%d. %s = %f\n", i, item->desc, *((value_t *)item->value));
      break;
    }

    item++;
    i++;
  }

  printf("0. Save and exit\n\nEnter setting to change or 0 to save: ");
  fflush(stdout);
}

/************************************************************************
 * Reads a line of input from the console.  Allows rudamentary line
 * editing using backspace/delete.  Control-C exits, Control-U restarts
 ************************************************************************/
int read_line(char *buf, size_t size) {
  char *p = buf;
  for (;;) {
    char c = read_char();
    if (c >= 32 && c < 127 && p < buf + size) {
      /* Append character to buffer */
      *p++ = c;
      write_char(c);
    } else if ((c == 8 || c == 127) && p > buf) {
      p--;
      write_char(8);
    } else if (c == 13) {
      /* Accept input */
      *p = 0;
      write_char(c);
      return 1;
    } else if (c == 3) {
      /* Abort */
      buf[0] = 0;
      return 0;
    } else if (c == 10) {
      /* Ignore*/
      write_char(c);
    } else if (c == 21) {
      /* Reset line */
      p = buf;
      printf("\n");
    } else if (c) {
      /* Unknown character */
      write_char('!');
    }
  }
}

/************************************************************************
 * Prompts the user to edit a single item.
 ************************************************************************/
void edit_item(const config_item_t *item) {
  printf("\nEnter new value: ");
  fflush(stdout);

  if (read_line(buf, sizeof(buf))) {
    if (item->type == CONFIG_STR) {
      char *dest = (char *)item->value;
      strncpy(dest, buf, item->size);
      dest[item->size - 1] = 0;
    } else if (item->type == CONFIG_VALUE) {
      if (sscanf(buf, "%f", (float *)item->value) != 1) {
        printf("Invalid value %s\n", buf);
      }
    }
  }
}

/************************************************************************
 * Reads a single character from the console.  Returns 0 if not pressed
 * in 10 seconds
 ************************************************************************/
char read_char() {
  char c;
  if (uart_read_bytes(CONFIG_UART, &c, 1, pdMS_TO_TICKS(10000)) == 1) {
    return c;
  } else {
    return 0;
  }
}

/************************************************************************
 * Writes a single character to the console
 ************************************************************************/
void write_char(char c) { uart_write_bytes(CONFIG_UART, &c, 1); }
