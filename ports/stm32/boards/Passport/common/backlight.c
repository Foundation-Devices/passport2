// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Backlight driver for LED

#include "stm32h7xx_hal.h"

#include "backlight.h"

// Get a pointer to the CCR for the PWM on the timer channel
#define BACKLIGHT_PWM_CCR() ((volatile uint32_t*)&(backlight_timer_handle.Instance->CCR1) + (TIM_CHANNEL_3 >> 2))
// Adjust this to fine tune the maximum illumination
#define BACKLIGHT_PWM_TIM_PERIOD (50000)

static TIM_HandleTypeDef backlight_timer_handle;

// Set up timer 4 to drive the backlight LED.
// Currently starts the timer and turns on the backlight.
void backlight_init(void) {
    TIM_MasterConfigTypeDef sMasterConfig   = {0};
    TIM_OC_InitTypeDef      sConfigOC       = {0};
    GPIO_InitTypeDef        GPIO_InitStruct = {0};

    __TIM4_CLK_ENABLE();

    backlight_timer_handle.Instance = TIM4;

    /* Prescale = 10 gives about 331 Hz 200 - 400Hz ideal */
    backlight_timer_handle.Init.Prescaler         = 10; /* Default for 480 MHz */
    backlight_timer_handle.Init.CounterMode       = TIM_COUNTERMODE_UP;
    backlight_timer_handle.Init.Period            = 65535;
    backlight_timer_handle.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    backlight_timer_handle.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_PWM_Init(&backlight_timer_handle);

    sMasterConfig.MasterOutputTrigger = TIM_TRGO_RESET;
    sMasterConfig.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
    HAL_TIMEx_MasterConfigSynchronization(&backlight_timer_handle, &sMasterConfig);

    sConfigOC.OCMode     = TIM_OCMODE_PWM1;
    sConfigOC.Pulse      = 32768;
    sConfigOC.OCPolarity = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCFastMode = TIM_OCFAST_DISABLE;
    HAL_TIM_PWM_ConfigChannel(&backlight_timer_handle, &sConfigOC, TIM_CHANNEL_3);

    GPIO_InitStruct.Pin       = GPIO_PIN_8;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM4;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);
}

// Only initialize what's necessary for the firmware to takeover control of the backlight since the main
// backlight_init() function was already called by the bootloader. If we call the full init again, the backlight
// turns off for a couple of seconds during startup, which is not good UX.
void backlight_minimal_init(void) {
    backlight_timer_handle.Instance = TIM4;
}

/*
 * backlight_intensity()
 * Adjusts intensity of the backlight when passed a value between 0 and 100.
 * 0 - Turns off backlight, 100 is maximum
 * Param: uint16_t intensity
 * Returns: Nothing
 */

void backlight_intensity(uint16_t intensity) {
    if (intensity == 0) {
        /* Turn backlight timer off */
        HAL_TIM_PWM_Stop(&backlight_timer_handle, TIM_CHANNEL_3);
    } else if (intensity > 0 && intensity <= 100) {
        /* Ensure backlight timer is on */
        HAL_TIM_PWM_Start(&backlight_timer_handle, TIM_CHANNEL_3);

        /* Sets intensity using Timer 4 PWM pulse width */
        *BACKLIGHT_PWM_CCR() = intensity * (BACKLIGHT_PWM_TIM_PERIOD - 1) / 100;
    }
}

void backlight_adjust(bool turbo) {
    HAL_TIM_PWM_Stop(&backlight_timer_handle, TIM_CHANNEL_3);
    if (turbo)
        backlight_timer_handle.Init.Prescaler = 10;
    else
        backlight_timer_handle.Init.Prescaler = 1;
    TIM_Base_SetConfig(backlight_timer_handle.Instance, &backlight_timer_handle.Init);
    HAL_TIM_PWM_Start(&backlight_timer_handle, TIM_CHANNEL_3);
}
