# ESP32/Arduino humidity, temperature, and power sensor.

## Building The Firmware

To compile this firmware you will need to:

1. Install the Arduino IDE and ESP32 extensions [See here](https://learn.adafruit.com/adafruit-itsybitsy-esp32/arduino-ide-setup)
2. Choose Board esp32->ESP32 Dev Module
3. Install the requisite libraries:
a. [Pub Sub Client](https://pubsubclient.knolleary.net/) 3.0.4
b. [Adafruit Sensor Library] (https://github.com/adafruit/Adafruit_Sensor) 1.1.14
c. [Adafruit DHT](https://github.com/adafruit/DHT-sensor-library) version 1.4.6
4. Connect the ESP32 board
5. Press Control-U to compile and upload

Newer versions may work, these are the ones I have tested.

## Legal Stuff

This software comes with no warranty whatsoever.  Use it at your own
risk.  The author places no restrictions on redistribution, including
commercial applications.
