#include <Arduino.h>
#include "Settings.h"

/* Reads a line from the serial port.  Includes echo and
    editing functionality (backspace, delete, Ctrl-U)
*/
int read_string(const char* prompt, char* buf, int maxlen) {
  char* pos = buf;
  char c;

  Serial.print(prompt);
  Serial.print("-> ");

  for (;;) {
    if (!Serial.available()) {
      delay(10);
      continue;
    }

    char c = Serial.read();
    if (c >= 32 && c < 127 && pos - buf < maxlen) {
      // Normal character
      Serial.write(c);  // Echo character
      *pos++ = c;       // Append to buffer
    } else if (c == '\n' || c == '\r') {
      // End of line
      *pos = 0;
      Serial.println();
      return pos - buf;
    } else if ((c == '\b' || c == 127) && pos > buf) {
      // Backspace or delete
      pos--;
      Serial.write('\b');
    } else if (c == 0x15) {
      // Kill (Ctrl-U)
      Serial.println();
      Serial.print(prompt);
      Serial.print("->");
      pos = buf;
    } else {
      // Unknown character
      Serial.write('\a'); // Bell
    }
  }
}

boolean read_int(const char* prompt, int* value, int min_value, int max_value) {
  char buf[8];

  for (;;) {
    if (read_string(prompt, buf, sizeof(buf)) <= 0) {
      // Unchanged
      return false;
    }

    int new_val = atoi(buf);
    if (new_val < min_value || new_val > max_value) {
      Serial.print("Must be between ");
      Serial.print(min_value);
      Serial.print(" and ");
      Serial.println(max_value);
    } else {
      *value = new_val;
      return true;
    }
  }
}


boolean read_float(const char* prompt, float* value, float min_value, float max_value) {
  char buf[8];

  for (;;) {
    if (read_string(prompt, buf, sizeof(buf)) <= 0) {
      // Unchanged
      return false;
    }

    float new_val = atof(buf);
    if (new_val < min_value || new_val > max_value) {
      Serial.print("Must be between ");
      Serial.print(min_value);
      Serial.print(" and ");
      Serial.println(max_value);
    } else {
      *value = new_val;
      return true;
    }
  }
}


Config::Config(const char* name) {
  _name = name;
}

ConfigString::ConfigString(const char* name, char* value, int min_length, int max_length, const char* default_value) : Config(name) {
  _value = value;
  _min_length = min_length;
  _max_length = max_length;
  _default = default_value;
}

void ConfigString::apply_default() {
  strncpy(_value, _default, _max_length);
}

void ConfigString::print() {
  Serial.print(_name);
  Serial.print(" (");
  Serial.print(_value);
  Serial.print(")");
}

int ConfigString::read() {
  char buf[512];

  // TODO - min_length
  if (read_string(_name, buf, _max_length)) {
    strcpy(_value, buf);
    return true;
  } else {
    return false;
  }
}

ConfigSecret::ConfigSecret(const char* name, char* value, int min_length, int max_length) :
  ConfigString(name, value, min_length, max_length, "") {
}

void ConfigSecret::print() {
  Serial.print(_name);
  Serial.print(" (");
  for (int i = 0; i < strlen(_value); i++) {
    Serial.print("*");
  }
  Serial.print(")");
};

ConfigInt::ConfigInt(const char* name, int* value_ptr, int min_value, int max_value, int default_value) :
  Config(name) {
  _value_ptr = value_ptr;
  _default = default_value;
  _min_value = min_value;
  _max_value = max_value;
}

void ConfigInt::apply_default() {
  *_value_ptr = _default;
}

void ConfigInt::print() {
  Serial.print(_name);
  Serial.print(" (");
  Serial.print(*_value_ptr);
  Serial.print(")");
}

int ConfigInt::read() {
  return read_int(_name, _value_ptr, _min_value, _max_value);
}

ConfigFloat::ConfigFloat(const char* name, float* value_ptr, float min_value, float max_value, float default_value) :
  Config(name) {
  _value_ptr = value_ptr;
  _default = default_value;
  _min_value = min_value;
  _max_value = max_value;
}

void ConfigFloat::apply_default() {
  *_value_ptr = _default;
}

void ConfigFloat::print() {
  Serial.print(_name);
  Serial.print(" (");
  Serial.print(*_value_ptr);
  Serial.print(")");
}

int ConfigFloat::read() {
  return read_float(_name, _value_ptr, _min_value, _max_value);
}

SettingsManager::SettingsManager(Config** configs, int count) {
  _configs = configs;
  _count = count;
}
void SettingsManager::apply_defaults() {
  for (int i = 0; i < _count; i++) {
    _configs[i]->apply_default();
  }
}

void SettingsManager::print_all() {
  Serial.println("Current settings:");
  for (int i = 0; i < _count; i++) {
    Serial.print("    ");
    Serial.print(i + 1);
    Serial.print(". ");
    _configs[i]->print();
    Serial.println();
  }
}

boolean SettingsManager::edit_config() {
  for (;;) {
    int choice;
    if (read_int("Choose item to change or 0 to save", &choice, 0, _count)) {
      if (choice == 0) {
        return true;
      } else {
        _configs[choice - 1]->read();
        print_all();
      }
    }
  }
}
