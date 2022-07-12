// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// factory-test.c - Code for testing Passport boards before final provisioning and lockdown.

#include <string.h>
#include <stdbool.h>
#include <stdlib.h>
#include <limits.h>

#include "lvgl.h"
#include "images.h"
#include "backlight.h"
#include "factory-test.h"
#include "utils.h"
#include "gpio.h"
#include "delay.h"
#include "ui.h"
#include "display.h"
#include "spiflash.h"
#include "splash.h"
#include "se.h"
#include "adc.h"
#include "noise.h"
#include "bq27520.h"
#include "i2c-init.h"
#include "camera-ovm7690.h"
#include "stm32h7xx_hal.h"
#include "eeprom.h"
#include "fwheader.h"
#include "verify.h"
#include "update.h"

volatile FactoryTestInfo* pFactoryTestInfo = (FactoryTestInfo*)SRAM4_START;

void show_text(char* text) {
    display_fill(COLOR_WHITE);
    ui_draw_wrapped_text(10, 10, 230, text, true);
    display_show();
}

void factory_test_set_result_success() {
    pFactoryTestInfo->result_code = FACTORY_TEST_OK;
    strcpy((char*)pFactoryTestInfo->message, "OK");
}

void factory_test_set_result_ask_confirmation() {
    pFactoryTestInfo->result_code = FACTORY_TEST_PLEASE_CONFIRM;
    strcpy((char*)pFactoryTestInfo->message, "Please Confirm");
}

void factory_test_set_result_error(uint32_t result_code, char* message) {
    strncpy((char*)pFactoryTestInfo->message, message, FACTORY_TEST_MESSAGE_MAX_LEN);
    pFactoryTestInfo->result_code = result_code;
}

void factory_test_set_message(char* message) {
    strncpy((char*)pFactoryTestInfo->message, message, FACTORY_TEST_MESSAGE_MAX_LEN);
}

void factory_test_set_progress(uint32_t percent_complete) {
    pFactoryTestInfo->progress = percent_complete;
}

void (*factory_test_funcs[FACTORY_TEST_MAX_FUNCTION_NUM])(uint32_t param1, uint32_t param2) = {
    factory_test_lcd,
    factory_test_camera,
    factory_test_eeprom,
    factory_test_keypad,
    factory_test_sd_card,
    factory_test_fuel_gauge,
    factory_test_external_flash,
    factory_test_secure_element,
    factory_test_avalanche_noise_source
};

void factory_test_loop() {
    char buf[64];

    int counter = 0;
    while (true) {
        itoa(counter, buf, 10);
        show_text(buf);

        // See if a new function was written to memory by the provisioning tool
        if (pFactoryTestInfo->progress == FACTORY_TEST_COMMAND_READY) {
            factory_test_set_progress(0);
            if (pFactoryTestInfo->function <= FACTORY_TEST_MAX_FUNCTION_NUM) {
                factory_test_funcs[pFactoryTestInfo->function - 1](pFactoryTestInfo->param1, pFactoryTestInfo->param2);
            } else {
                factory_test_set_result_error(FACTORY_TEST_ERROR_UNKNOWN_FUNCTION, "Unknown function number received.");
            }

            show_text((char*)pFactoryTestInfo->message);
            delay_ms(1500);

            // We tell the provisioning tool we're done even if we didn't call the function, since this
            // is what it polls for to known when a command is complete.
            factory_test_set_progress(100);
        }
        counter++;
        delay_ms(1000);
    }
}

void factory_test_lcd(uint32_t param1, uint32_t param2) {
    int speedx = 10, speedy = 10;
    uint16_t x = 115, y = 135;
    const uint16_t WIDTH = 100;
    const uint16_t HEIGHT = 100;

    // Test for shorts on LCD lines

    typedef struct _port_pin {
        GPIO_TypeDef* port;
        uint32_t pin;
    } port_pin_t;

    const int NUM_PINS = 5;
    port_pin_t lcd_pins[] = {
        { GPIOA, GPIO_PIN_8  }, // RST
        { GPIOE, GPIO_PIN_15 }, // DC
        { GPIOA, GPIO_PIN_15 }, // CS
        { GPIOA, GPIO_PIN_5  }, // SPI - SCK
        { GPIOA, GPIO_PIN_7  }, // SPI - MOSI
    };

    GPIO_InitTypeDef GPIO_InitStruct = {0};

    for (int current_pin = 0; current_pin < NUM_PINS; current_pin++) {
        // Set other than current pins as pull-down inputs
        for (int p = 0; p < NUM_PINS; p++) {
            if (p != current_pin) {
                HAL_GPIO_WritePin(lcd_pins[p].port, lcd_pins[p].pin, GPIO_PIN_RESET);
                GPIO_InitStruct.Pin   = lcd_pins[p].pin;
                GPIO_InitStruct.Mode  = GPIO_MODE_INPUT;
                GPIO_InitStruct.Pull  = GPIO_PULLDOWN;
                GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
                HAL_GPIO_Init(lcd_pins[p].port, &GPIO_InitStruct);
            }
        }

        // Set the current pin as output and assert HIGH signal
        GPIO_InitStruct.Pin   = lcd_pins[current_pin].pin;
        GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
        GPIO_InitStruct.Pull  = GPIO_NOPULL;
        GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
        HAL_GPIO_Init(lcd_pins[current_pin].port, &GPIO_InitStruct);
        HAL_GPIO_WritePin(lcd_pins[current_pin].port, lcd_pins[current_pin].pin, GPIO_PIN_SET);

        // Check that other pins aren't HIGH otherwise there's a short
        for (int p = 0; p < NUM_PINS; p++) {
            if (p != current_pin) {
                if (HAL_GPIO_ReadPin(lcd_pins[p].port, lcd_pins[p].pin)) {
                    factory_test_set_result_error(107, "Short LCD pins detected");
                    return;
                }
            }
        }

        HAL_GPIO_WritePin(lcd_pins[current_pin].port, lcd_pins[current_pin].pin, GPIO_PIN_RESET);
    }

    // Reinitialize LCD since we messed with its pins before
    display_init(true);

    factory_test_set_progress(50);

    uint16_t intensity = 100;
    bool intensity_up = false;

    int total_time_ms = 1000 * 3; // 3s
    while (total_time_ms > 0) {
        backlight_intensity(intensity);

        if (intensity_up) {
            intensity += 5;
            if (intensity >= 100) {
                intensity_up = false;
            }
        } else {
            intensity -= 5;
            if (intensity <= 5) {
                intensity_up = true;
            }
        }

        display_fill(COLOR_WHITE);
        ui_draw_wrapped_text(0, 5, 230, "LCD TEST, PLEASE CHECK FOR ABNORMALITIES", true);
        display_image(
            x, y,
            LARGE_ICON_ERROR.header.w, LARGE_ICON_ERROR.header.h,
            LARGE_ICON_ERROR.data,
            lv_cf_mode_to_draw_mode(LARGE_ICON_ERROR.header.cf)
        );
        display_show();

        x += speedx;
        y += speedy;
        if(x + WIDTH >= SCREEN_WIDTH || x <= 0) {
            speedx *= -1;
        }
        if(y + HEIGHT >= SCREEN_HEIGHT || y <= 80) {
            speedy *= -1;
        }

        delay_ms(50);
        total_time_ms -= 100; // -100 instead of -50 to account for other delays
    }

    factory_test_set_progress(100);
    factory_test_set_result_success();
}

void factory_test_camera(uint32_t param1, uint32_t param2) {
    #define CAMERA_I2C_ADDR (0x21 << 1)  // Use 8-bit address

    GPIO_InitTypeDef        GPIO_InitStruct    = {0};

    /* TIM3 GPIO Configuration: PB1 -> TIM3_CH4 */
    GPIO_InitStruct.Pin       = GPIO_PIN_1;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    uint16_t period = (SystemCoreClock / 24000000); /* Need 24 MHz clock for the camera */

    __TIM3_CLK_ENABLE();
    TIM_HandleTypeDef  tim3;
    TIM_MasterConfigTypeDef tim3_master_config = {0};
    TIM_OC_InitTypeDef      tim3_pwm_config    = {0};

    tim3.Instance               = TIM3;
    tim3.Init.Prescaler         = 0;
    tim3.Init.CounterMode       = TIM_COUNTERMODE_UP;
    tim3.Init.Period            = period - 1;
    tim3.Init.ClockDivision     = 0;
    tim3.Init.RepetitionCounter = 0;
    tim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if (HAL_TIM_PWM_Init(&tim3) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to init camera clock PWM");
        return;
    }

    tim3_master_config.MasterOutputTrigger = TIM_TRGO_RESET;
    tim3_master_config.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
    if (HAL_TIMEx_MasterConfigSynchronization(&tim3, &tim3_master_config) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to init camera clock");
        return;
    }

    /* PWM configuration */
    tim3_pwm_config.OCMode     = TIM_OCMODE_PWM1;
    tim3_pwm_config.Pulse      = period / 2;
    tim3_pwm_config.OCPolarity = TIM_OCPOLARITY_HIGH;
    tim3_pwm_config.OCFastMode = TIM_OCFAST_DISABLE;
    if (HAL_TIM_PWM_ConfigChannel(&tim3, &tim3_pwm_config, TIM_CHANNEL_4) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to init camera clock");
        return;
    }
    HAL_TIM_PWM_Start(&tim3, TIM_CHANNEL_4);

    GPIO_InitStruct.Pin   = GPIO_PIN_7;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* Reset camera, power down pin is active high */
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, GPIO_PIN_SET);
    delay_ms(20);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, GPIO_PIN_RESET);
    delay_ms(20);

    /* I2C1 Pin configuration */
    GPIO_InitStruct.Pin       = GPIO_PIN_6 | GPIO_PIN_9;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_OD;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    __HAL_RCC_I2C1_CLK_ENABLE();
    I2C_HandleTypeDef  hi2c1;
    hi2c1.Instance    = I2C1;
    hi2c1.Init.Timing = 0x00B07FFF; /* 0x00100727 - 300 KHz @ 64 MHz */
                                    /* 0x00B07FFF - 300 KHz @ 480 MHz */
    hi2c1.Init.OwnAddress1      = 0;
    hi2c1.Init.AddressingMode   = I2C_ADDRESSINGMODE_7BIT;
    hi2c1.Init.DualAddressMode  = I2C_DUALADDRESS_DISABLE;
    hi2c1.Init.OwnAddress2      = 0;
    hi2c1.Init.OwnAddress2Masks = I2C_OA2_NOMASK;
    hi2c1.Init.GeneralCallMode  = I2C_GENERALCALL_DISABLE;
    hi2c1.Init.NoStretchMode    = I2C_NOSTRETCH_DISABLE;
    if (HAL_I2C_Init(&hi2c1) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to init camera I2C");
        return;
    }

    uint8_t data = 0;
    uint8_t reg = 0x0E;
    if (HAL_I2C_Master_Transmit(&hi2c1, CAMERA_I2C_ADDR, &reg, 1, 100) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to write register address to camera");
        return;
    }
    if (HAL_I2C_Master_Receive(&hi2c1, CAMERA_I2C_ADDR, &data, 1, 100) != HAL_OK) {
        factory_test_set_result_error(106, "Failed to read camera register");
        return;
    }

    factory_test_set_result_success();
}

void factory_test_eeprom(uint32_t param1, uint32_t param2) {
    i2c_init();

    if (eeprom_init(&g_hi2c2) != HAL_OK) {
        factory_test_set_result_error(105, "Failed to init EEPROM");
        return;
    }

    uint8_t buf[32] = { 0, };
    for (int i = 0; i < sizeof(buf); i++) {
        buf[i] = i;
    }

    if (eeprom_write(0x00, (uint8_t *)&buf, sizeof(buf)) != HAL_OK) {
        factory_test_set_result_error(105, "EEPROM write failed");
        return;
    }
    memset(&buf, 0, sizeof(buf));

    if (eeprom_read(0x00, (uint8_t *)&buf, sizeof(buf)) != HAL_OK) {
        factory_test_set_result_error(105, "EEPROM read failed");
        return;
    }

    for (int i = 0; i < sizeof(buf); i++) {
        if (buf[i] != i) {
            ui_show_hex_buffer("EEPROM", (uint8_t *) &buf, sizeof(buf));
            factory_test_set_result_error(105, "EEPROM read incorrect pattern");
            return;
        }
    }

    factory_test_set_result_success();
}

void factory_test_keypad(uint32_t param1, uint32_t param2) {
    factory_test_set_progress(100);
    factory_test_set_result_success();
}

void factory_test_sd_card(uint32_t param1, uint32_t param2) {
    GPIO_InitTypeDef GPIO_InitStruct = {0};

    __HAL_RCC_GPIOE_CLK_ENABLE();
    GPIO_InitStruct.Pin = GPIO_PIN_3;
    GPIO_InitStruct.Mode = GPIO_MODE_INPUT;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    // An empty SD card slot has a "card detect" pin pulled up.
    // It's pulled down when an SD card is inserted
    if (HAL_GPIO_ReadPin(GPIOE, GPIO_PIN_3)) {
        factory_test_set_result_error(101, "No SD card detected. Insert the SD card");
        return;
    }

    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};
    PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_SDMMC;
    PeriphClkInitStruct.SdmmcClockSelection = RCC_SDMMCCLKSOURCE_PLL;
    if (HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct) != HAL_OK) {
        factory_test_set_result_error(101, "Unable to setup PLL for SDMMC1");
        return;
    }

    factory_test_set_progress(33);

    __HAL_RCC_SDMMC1_CLK_ENABLE();
    __HAL_RCC_GPIOC_CLK_ENABLE();
    __HAL_RCC_GPIOD_CLK_ENABLE();
    // Reset SDMMC
    __HAL_RCC_SDMMC1_FORCE_RESET();
    __HAL_RCC_SDMMC1_RELEASE_RESET();
    GPIO_InitStruct.Pin = GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10|GPIO_PIN_11|GPIO_PIN_12;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF12_SDIO1;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);
    GPIO_InitStruct.Pin = GPIO_PIN_2;
    GPIO_InitStruct.Mode = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_VERY_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF12_SDIO1;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);
    SD_HandleTypeDef hsd;
    hsd.Instance = SDMMC1;
    hsd.Init.ClockEdge = SDMMC_CLOCK_EDGE_RISING;
    hsd.Init.ClockPowerSave = SDMMC_CLOCK_POWER_SAVE_ENABLE;
    hsd.Init.BusWide = SDMMC_BUS_WIDE_4B;
    hsd.Init.HardwareFlowControl = SDMMC_HARDWARE_FLOW_CONTROL_DISABLE;
    hsd.Init.ClockDiv = SDMMC_NSpeed_CLK_DIV;
    if (HAL_SD_Init(&hsd) != HAL_OK) {
        factory_test_set_result_error(101, "Unable to setup SDMMC1");
        return;
    }

    factory_test_set_progress(66);

    if (HAL_SD_InitCard(&hsd) != HAL_OK) {
        factory_test_set_result_error(101, "Unable to setup SD card");
        return;
    }

    factory_test_set_result_success();
}

void factory_test_fuel_gauge(uint32_t param1, uint32_t param2) {
    bq27520_init();

    if (bq27520_probe() != HAL_OK) {
        factory_test_set_result_error(104, "Can't connect to fuel gauge chip");
        bq27520_deinit();
        return;
    }

    bq27520_deinit();
    factory_test_set_result_success();
}

// Returns true if timed out
bool busy_wait(void) {
    int timeout_ms = 30 * 1000; // 30s
    int elapsed_ms = 0;

    while (true) {
        bool is_busy = false;
        if (spi_is_busy(&is_busy) != HAL_OK) {
            factory_test_set_result_error(100, "spi_is_busy() failed");
            return false;
        }

        if (elapsed_ms >= timeout_ms) {
            return true;
        }

        if (!is_busy) {
            break;
        }

        delay_ms(10);
        elapsed_ms += 10;
    }

    return false;
}

void factory_test_external_flash(uint32_t param1, uint32_t param2) {
#if 0 /* Disabled for speed */
    uint8_t buf[32] = { 0x00 };
    uint8_t buf_pattern[32];
    const int PAGE_SIZE = 1024;

    for (int i = 0; i < sizeof(buf_pattern); i++) {
        buf_pattern[i] = i;
    }
#endif /* if 0 */

    show_text("Setting up FLASH SPI...");

    if (spi_setup() != HAL_OK) {
        factory_test_set_result_error(100, "spi_setup() failed");
        return;
    }

    factory_test_set_progress(25);

    show_text("Reading SPI FLASH ID...");

    uint32_t id = 0;
    if (spi_read_id(&id) != HAL_OK) {
        factory_test_set_result_error(100, "spi_read_id() failed");
        return;
    }

    if (id != WINBOND_FLASH_ID_1 && id != WINBOND_FLASH_ID_2) {
        factory_test_set_result_error(100, "Unexpected SPI FLASH ID");
        return;
    }

    factory_test_set_progress(100);
#if 0 /* Disabled for speed */
    show_text("Erasing SPI FLASH...");
    if (spi_chip_erase() != HAL_OK) {
        factory_test_set_result_error(100, "spi_chip_erase() failed");
        return;
    }

    if (busy_wait()) {
        factory_test_set_result_error(100, "Timeout exceeded while waiting for SPI flash");
        return;
    }
    if (pFactoryTestInfo->result_code == 100) {
        // An error occurred during busy_wait
        return;
    }

    factory_test_set_progress(60);

    show_text("Verifying erased...");
    if (spi_read(0, sizeof(buf), (uint8_t *) &buf) != HAL_OK) {
        factory_test_set_result_error(100, "spi_read() failed");
        return;
    }

    for (int i = 0; i < sizeof(buf); i++) {
        if (buf[i] != 0xFF) {
            factory_test_set_result_error(100, "0xFF pattern failed");
            return;
        }
    }

    factory_test_set_progress(70);

    show_text("Writing test pattern...");
    for (int chunk = 0; chunk < PAGE_SIZE / sizeof(buf_pattern); chunk++) {
        if (spi_write(sizeof(buf_pattern) * chunk, sizeof(buf_pattern), (uint8_t *) &buf_pattern) != HAL_OK) {
            factory_test_set_result_error(100, "pattern spi_write() failed");
            return;
        }

        if (busy_wait()) {
            factory_test_set_result_error(100, "Timeout exceeded while waiting for SPI flash");
            return;
        }
        if (pFactoryTestInfo->result_code == 100) {
            // An error occurred during busy_wait
            return;
        }
    }

    factory_test_set_progress(80);

    show_text("Verifying test pattern...");
    for (int chunk = 0; chunk < PAGE_SIZE / sizeof(buf_pattern); chunk++) {
        if (spi_read(sizeof(buf_pattern) * chunk, sizeof(buf_pattern), (uint8_t *) &buf) != HAL_OK) {
            factory_test_set_result_error(100, "pattern spi_read() failed");
            return;
        }

        for (int i = 0; i < sizeof(buf_pattern); i++) {
            if (buf[i] != i) {
                factory_test_set_result_error(100, "pattern corrupted");
                return;
            }
        }
    }

    factory_test_set_progress(90);

    show_text("Erasing SPI FLASH again...");

    // Erase everything we've done
    if (spi_chip_erase() != HAL_OK) {
        factory_test_set_result_error(100, "spi_chip_erase() failed");
        return;
    }
    if (busy_wait()) {
        factory_test_set_result_error(100, "Timeout exceeded while waiting for SPI flash");
        return;
    }
    if (pFactoryTestInfo->result_code == 100) {
        // An error occurred during busy_wait
        return;
    }
#endif /* if 0 */
    if (spi_flash_deinit() != HAL_OK) {
        factory_test_set_result_error(100, "spi_deinit() failed");
        return;
    }

    factory_test_set_result_success();
}

void factory_test_secure_element(uint32_t param1, uint32_t param2) {
    se_setup();

    // Run self-test for SHA, ECDSA, RNG
    int res = se_run_selftest(true, false, false, true, true);
    if (res) {
        char buf[16] = {0,};
        itoa(res, buf, 16);
        factory_test_set_result_error(102, buf);

        return;
    }

    uint8_t config[128] = {0};
    int     rc          = se_config_read(config);
    if (rc < 0) {
        factory_test_set_result_error(102, "se_config_read() failed");
        return;
    }

    factory_test_set_progress(50);

    if (config[87] != 0x55) {
        factory_test_set_result_error(102, "SE config is locked");
        return;
    }

    if (config[86] != 0x55) {
        factory_test_set_result_error(102, "SE data is locked");
        return;
    }

    factory_test_set_result_success();
}

void factory_test_avalanche_noise_source(uint32_t param1, uint32_t param2) {
    adc_init();
    noise_enable();

    // An ideal RNG should produce random numbers without bias.
    // e.g. with a uniform distribution. When random numbers get put into fixed number of buckets
    // by a number of occurrences (frequency), the average among these buckets should equal
    // the number of tests divided by the number of buckets.
    // And at least half of the buckets should contain at least one number.
    // That way it's possible to verify that each number has an equal probability to appear
    // in any of the buckets and there is no bias.

    uint8_t buckets[32] = {0};
    const int NUM_STEPS = 128;
    for (int i = 0; i < NUM_STEPS; i++) {
        uint16_t word = 0;
        if (!noise_get_random_uint16((uint16_t *)&word)) {
            factory_test_set_result_error(103, "noise_get_random_uint16() failed");
            noise_disable();
            return;
        }

        if (buckets[word % sizeof(buckets)] < UCHAR_MAX) {
            buckets[word % sizeof(buckets)] += 1;
        }
    }

    int num_buckets_filled = 0;
    int avg = 0;
    for (int i = 0; i < sizeof(buckets); i++) {
        if (buckets[i]) {
            num_buckets_filled += 1;
        }
        avg += buckets[i];
    }
    avg /= sizeof(buckets);

    bool at_least_half_filled = num_buckets_filled >= sizeof(buckets) / 2;
    if (!at_least_half_filled || avg != NUM_STEPS / sizeof(buckets)) {
        factory_test_set_result_error(103, "Non-uniform distribution");
        noise_disable();
        return;
    }

    noise_disable();
    factory_test_set_result_success();
}
