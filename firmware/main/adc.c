#include <math.h>
#include <string.h>

#include "config.h"
#include "esp_adc/adc_cali.h"
#include "esp_adc/adc_cali_scheme.h"
#include "esp_adc/adc_continuous.h"
#include "esp_check.h"
#include "esp_log.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

/* Sample 60 kHz/ch over 10 line cycles at 60 Hz -> 10K samples/ch per window.
 * 500 samples/ch/frame divides evenly so windows align with frames. */
#define SAMPLE_RATE 60000
#define SAMPLES_PER_CH 10000
#define SAMPLES_PER_FRAME 500
#define CONV_FRAME_SIZE (SAMPLES_PER_FRAME * SOC_ADC_DIGI_RESULT_BYTES)

static const adc_atten_t ATTEN = ADC_ATTEN_DB_12;
static const adc_bitwidth_t WIDTH = ADC_BITWIDTH_12;

static const char *TAG = "adc_rms";

static adc_continuous_handle_t adc_h = NULL;

esp_err_t adc_init(void) {
  adc_continuous_handle_cfg_t adc_cfg = {
      .max_store_buf_size = CONV_FRAME_SIZE * 4,
      .conv_frame_size = CONV_FRAME_SIZE,
  };
  ESP_RETURN_ON_ERROR(adc_continuous_new_handle(&adc_cfg, &adc_h), TAG, "new");

  adc_digi_pattern_config_t pattern = {
      .atten = ATTEN,
      .channel = ADC_CHANNEL_0,
      .unit = ADC_UNIT_1,
      .bit_width = WIDTH,
  };

  adc_continuous_config_t dig_cfg = {
      .pattern_num = 1,
      .adc_pattern = &pattern,
      .sample_freq_hz = 60000,
      .conv_mode = ADC_CONV_SINGLE_UNIT_1,
      .format = ADC_DIGI_OUTPUT_FORMAT_TYPE2,
  };
  ESP_RETURN_ON_ERROR(adc_continuous_config(adc_h, &dig_cfg), TAG, "cfg");
  ESP_RETURN_ON_ERROR(adc_continuous_start(adc_h), TAG, "start");
  return ESP_OK;
}

/************************************************************************
 * Read current from snap-on transformer.  Blocks for 167ms.  Returns
 * RMS reading in volts.
 ************************************************************************/
esp_err_t adc_rms_read(value_t *rms_v) {
  ESP_RETURN_ON_FALSE(adc_h && rms_v, ESP_ERR_INVALID_STATE, TAG, "args");

  int64_t sum = 0;
  int64_t sq_sum = 0;
  int n = 0;

  while (n < SAMPLES_PER_CH) {
    adc_digi_output_data_t frame[SAMPLES_PER_FRAME];
    uint32_t bytes = 0;
    
    /* Read a frame of samples from the ADC */
    ESP_RETURN_ON_ERROR(
        adc_continuous_read(adc_h, (uint8_t *)frame, sizeof(frame), &bytes, 50),
        TAG, "read");

    /* Compute stats for the frame */
    adc_digi_output_data_t *p = frame;
    while (bytes) {
      uint16_t val = p->type2.data;
      sum += val;
      sq_sum += (int64_t)val * val;
      n++;

      /* Move to next sample */
      p++;
      bytes -= SOC_ADC_DIGI_RESULT_BYTES;
    }
  }

  /* Finally, compute the RMS from the accumulated stats */
  double mean = (double)sum / n;
  double mean_square = (double)sq_sum / n;
  double var = mean_square - mean * mean;
  if (var < 0) {
    var = 0;
  }

  /* 12-bit sensor returning 0-1 volts */
  *rms_v = sqrt(var) / 4096.0;

  return ESP_OK;
}
