/************************************************************************
  Humidity monitor for ESP32.

  (C) 2021 by Jim Shortz

  Runs continuously on an ESP32 microcontroller with DHT22 temp/humidity
  sensor and current transformer attached.  Publishes routine temperature,
  humidity, and power readings to an MQTT broker.
************************************************************************/
#include <WiFi.h>
#include <EEPROM.h>
#include <PubSubClient.h>
#include <DHT_U.h>
#include "Settings.h"

/* Compile-time settings */
const char* config_signature = "jshhumid";
const long baud = 115200;
const int power_led = 13;
const int dht_pin = 32;
const int current_pin = 36;
const unsigned long sample_period_us = 1000000 / 4;
const float amps_per_volt = 20;
const float vcc = 3.324;
long adc_mid = 1903;
const long adc_max = 4096;
const float line_voltage = 120;
const float power_factor = 0.96;
const float fan_threshold = 30; // Suppress power readings below this
const int mqtt_keepalive = 30;

/* Run-time configurable settings */
struct AppConfig {
  char  signature[8];           // Used to validate EEPROM contents

  char  ssid[16];
  char  wifi_password[64];
  char  mqtt_id[32];
  char  mqtt_host[128];
  int   mqtt_port;
  char  mqtt_user[32];
  char  mqtt_password[64];

  char  humid_topic[128];
  char  temp_topic[128];
  char  power_topic[128];

  float humid_cal;
  float temp_cal;

  int   report_period;  // seconds
} config;

Config* settings[] {
  new ConfigString("WiFi SSID", config.ssid, 1, sizeof(config.ssid), "TODO"),
  new ConfigSecret("WiFi Password", config.wifi_password, 1, sizeof(config.wifi_password)),

  new ConfigString("MQTT Client ID", config.mqtt_id, 1, sizeof(config.mqtt_id), "probie"),
  new ConfigString("MQTT Host", config.mqtt_host, 1, sizeof(config.mqtt_host), "io.adafruit.com"),
  new ConfigInt("MQTT Port", &config.mqtt_port, 1, 65535, 1883),
  new ConfigString("MQTT Username", config.mqtt_user, 0, sizeof(config.mqtt_user), ""),
  new ConfigSecret("MQTT Password", config.mqtt_password, 0, sizeof(config.mqtt_password)),

  new ConfigString("Humidity Topic", config.humid_topic, 1, sizeof(config.humid_topic), "humidity"),
  new ConfigString("Temperature Topic", config.temp_topic, 1, sizeof(config.temp_topic), "temperature"),
  new ConfigString("Power Topic", config.power_topic, 1, sizeof(config.power_topic), "power"),

  new ConfigFloat("Humidity Calibration", &config.humid_cal, -100, 100, 0),
  new ConfigFloat("Temperature Calibration", &config.temp_cal, -100, 100, 0),

  new ConfigInt("Reporting Interval (seconds)", &config.report_period, 0, 86400, 15)
};

SettingsManager mgr(settings, sizeof(settings) / sizeof(Config*));

/************************************************************************
  Globals
************************************************************************/
WiFiClient wifiClient;
PubSubClient mqttClient(wifiClient);
DHT dht(dht_pin, DHT22);

/************************************************************************
  Reads average from ADC.  Used to determine midpoint for RMS calc
************************************************************************/
long read_avg(long period) {
  long sum = 0;
  long count = 0;

  unsigned long start = micros();
  while (micros() - start < period) {
    long r = analogRead(current_pin);
    sum += r;
    count++;
  }
  return sum / count;
}

/************************************************************************
  Reads RMS voltage from current sensor
************************************************************************/
float read_rms(long period) {
  long sum = 0;
  long count = 0;

  unsigned long start = micros();
  while (micros() - start < period) {
    long r = analogRead(current_pin) - adc_mid;
    sum += r * r;
    count++;
  }
  return sqrt(sum / count) * vcc / (float)adc_max;
}

void wifi_connect() {
  Serial.println("Connecting to WiFi ");
  WiFi.begin(config.ssid, config.wifi_password);

  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.print("IP address: ");
  Serial.print(WiFi.localIP());
  Serial.print(" MAC address: ");
  Serial.print(WiFi.macAddress());
  Serial.print(" RSSI: ");
  Serial.println(WiFi.RSSI());
}

void init_config() {
  boolean write_config = false;

  // Read config from EEPROM
  EEPROM.begin(sizeof(config));
  EEPROM.get(0, config);

  // Make sure it's valid
  if (strncmp(config.signature, config_signature, sizeof(config.signature))) {
    Serial.println("No valid EEPROM config found - resetting to defaults.");
    memset(&config, 0, sizeof(config));
    strncpy(config.signature, config_signature, sizeof(config.signature));
    mgr.apply_defaults();
    mgr.print_all();
    write_config = true;
    mgr.edit_config();
  } else {
    char c;

    mgr.print_all();
    Serial.println("Press C to edit configuration");
    Serial.setTimeout(5000);

    if (Serial.readBytes(&c, 1) > 0 && tolower(c) == 'c') {
      write_config = mgr.edit_config();
    }
  }

  if (write_config) {
    EEPROM.put(0, config);
    EEPROM.commit();
    Serial.println("Changes saved to EEPROM");
  }
}

void calibrate_current() {
  adc_mid = read_avg(sample_period_us);
  Serial.print("Calibrated current sensor: adc_mid=");
  Serial.println(adc_mid);  
}

void setup() {
  Serial.begin(baud);
  Serial.println("Temperature/Humidity/Power Sensor v2.0 (C) 2021 - by Jim Shortz");
  init_config();


  calibrate_current();

  dht.begin();
  wifi_connect();
  pinMode(power_led, OUTPUT);
  digitalWrite(power_led, HIGH);
 
  mqttClient
  .setServer(config.mqtt_host, config.mqtt_port)
  .setKeepAlive(30);
}

boolean mqtt_connect() {
  Serial.print("Connecting to MQTT broker...");
  if (!mqttClient.connect(config.mqtt_id, config.mqtt_user, config.mqtt_password)) {
    Serial.print("Failed. Reason ");
    Serial.println(mqttClient.state());
    return false;
  } else {
    Serial.println("Connected");
  }

  return true;
}

void publish_metric(const char* topic, String data) {
  Serial.print("Publishing ");
  Serial.print(topic);
  Serial.print("=");
  Serial.print(data);

  if (!mqttClient.publish(topic, data.c_str())) {
    Serial.print(" FAILED");
  }
  Serial.println();
}

float read_power() {
  float current = read_rms(sample_period_us) * amps_per_volt;
  float power = current * line_voltage * power_factor;

  // Force low power readings to 0 to ignore measurement noise
  return (power >= fan_threshold) ? power : 0.0;
}

void publish_metrics() {
  digitalWrite(power_led, LOW);
  publish_metric(config.humid_topic, String(dht.readHumidity() + config.humid_cal, 1));
  publish_metric(config.temp_topic, String(dht.readTemperature(true) + config.temp_cal, 1));
  publish_metric(config.power_topic, String(read_power(), 0));
  digitalWrite(power_led, HIGH);
}

void print_time() {
  char buf[32];
  unsigned long ts = millis();
  snprintf(buf, sizeof(buf), "Waking up at %dd %02d:%02d:%02d.%03d", 
    ts / 86400000UL, (ts / 3600000UL) % 24, (ts/60000UL) % 60, (ts / 1000UL) % 60, ts % 1000UL);
  Serial.println(buf);  
}
void loop() {
  unsigned long wakeup = millis() + (unsigned long)(config.report_period * 1000);
  print_time();

  if (WiFi.status() == WL_CONNECTED) {
    if (mqttClient.loop() || mqtt_connect()) {
      publish_metrics();
    }
  }
  else {
    Serial.println("Attempting to reconnect WiFi");
    WiFi.reconnect();
  }

  unsigned long snooze = wakeup - millis();
  delay(snooze > 0 ? snooze : 10);
}
