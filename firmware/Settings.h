class Config {
  protected:
    const char* _name;
    Config(const char* name);

  public:
    virtual void apply_default() = 0;
    virtual int read() = 0;
    virtual void print() = 0;
};

class ConfigString : public Config {
  protected:
    char* _value;
    int _min_length;
    int _max_length;
    const char* _default;

  public:
    ConfigString(const char* name, char* value , int min_length, int max_length, const char* default_value);

    virtual void apply_default();
    virtual void print();
    virtual int read();
};

class ConfigSecret : public ConfigString {
  public:
    ConfigSecret(const char* name, char* value, int min_length, int max_length);
    virtual void print();
};

class ConfigInt : public Config {
  protected:
    int* _value_ptr;
    int _min_value;
    int _max_value;
    int _default;

  public:
    ConfigInt(const char* name, int* value_ptr , int min_value, int max_value, int default_value);

    virtual void apply_default();
    virtual void print();
    virtual int read();
};

class ConfigFloat : public Config {
  protected:
    float* _value_ptr;
    float _min_value;
    float _max_value;
    float _default;

  public:
    ConfigFloat(const char* name, float* value , float min_value, float max_value, float default_value);

    virtual void apply_default();
    virtual void print();
    virtual int read();
};

class SettingsManager {
  public:
    SettingsManager(Config** configs, int count);

    void apply_defaults();
    void print_all();
    boolean edit_config();

  protected:
    Config** _configs;
    int _count;
};
