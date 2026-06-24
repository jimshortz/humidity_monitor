idf_component_register(SRCS "main.c" "adc.c" "config.c"
                    INCLUDE_DIRS "."
                    REQUIRES
			esp_driver_i2c
			esp_driver_uart
                        esp_adc
                        esp_driver_gpio
                        esp_event
                        esp_netif
                        esp_wifi
                        mqtt
                        nvs_flash
                        )
                    
