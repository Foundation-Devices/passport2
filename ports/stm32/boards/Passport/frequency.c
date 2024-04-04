// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include "stm32h7xx_hal.h"

#ifndef FACTORY_TEST
#include <stdio.h>

#include "py/mperrno.h"
#include "py/mphal.h"
#include "py/mpstate.h"

#include "uart.h"
#else
#define printf(fmt, args...)
#endif

#include "backlight.h"
#include "frequency.h"
#include "se.h"

#define LOW_FREQUENCY 64000000
#define HIGH_FREQUENCY 480000000

static uint8_t turbo_count = 0;

#ifndef FACTORY_TEST
static uint8_t        rxbuf[260];
static pyb_uart_obj_t pyb_uart_repl_obj;

void frequency_update_console_uart(void) {
    pyb_uart_repl_obj.base.type    = &pyb_uart_type;
    pyb_uart_repl_obj.uart_id      = MICROPY_HW_UART_REPL;
    pyb_uart_repl_obj.is_static    = true;
    pyb_uart_repl_obj.timeout      = 0;
    pyb_uart_repl_obj.timeout_char = 2;
    uart_init(&pyb_uart_repl_obj, MICROPY_HW_UART_REPL_BAUD, UART_WORDLENGTH_8B, UART_PARITY_NONE, UART_STOPBITS_1, 0);
    uart_set_rxbuf(&pyb_uart_repl_obj, sizeof(rxbuf), rxbuf);
    MP_STATE_PORT(pyb_stdio_uart) = &pyb_uart_repl_obj;
}
#endif

void frequency_turbo_toggle(bool enable) {
    HAL_StatusTypeDef        rc;
    RCC_ClkInitTypeDef       RCC_ClkInitStruct   = {0};
    RCC_OscInitTypeDef       RCC_OscInitStruct   = {0};
    RCC_PeriphCLKInitTypeDef PeriphClkInitStruct = {0};

    // printf("[%s] enable=%s\n", __func__, enable ? "true" : "false");

    // HACK: TEMP - always be in high speed mode
    enable = true;

    // if ((!enable && (SystemCoreClock == LOW_FREQUENCY)) || (enable && (SystemCoreClock == HIGH_FREQUENCY)))
    //    return; /* Already at requested frequency...nothing to do */

    RCC->CR |= RCC_CR_HSION;

    /* Wait till HSI is ready */
    while (!(RCC->CR & RCC_CR_HSIRDY))
        ;

    /* Select HSI clock as main clock */
    RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_HSI;
    // RCC->CFGR = (RCC->CFGR & ~(RCC_CFGR_SW)) | RCC_CFGR_SW_PLL1;

    /* Reconfigure the clocks based on enable flag:
     *   64 MHz core clock if false
     *  480 MHz core clock if true
     */
    RCC_OscInitStruct.OscillatorType = RCC_OSCILLATORTYPE_HSE | RCC_OSCILLATORTYPE_HSI48;
    RCC_OscInitStruct.HSEState       = RCC_HSE_ON;
    RCC_OscInitStruct.HSIState       = RCC_HSI_OFF;
    RCC_OscInitStruct.CSIState       = RCC_CSI_OFF;
    RCC_OscInitStruct.LSEState       = RCC_LSE_OFF;
    RCC_OscInitStruct.HSI48State     = RCC_HSI48_ON;
    RCC_OscInitStruct.PLL.PLLSource  = RCC_PLLSOURCE_HSE;
    RCC_OscInitStruct.PLL.PLLState   = RCC_PLL_ON;
    RCC_OscInitStruct.PLL.PLLRGE     = RCC_PLL1VCIRANGE_1;
    RCC_OscInitStruct.PLL.PLLVCOSEL  = RCC_PLL1VCOWIDE;
    RCC_OscInitStruct.PLL.PLLFRACN   = 0;

    RCC_ClkInitStruct.ClockType =
        (RCC_CLOCKTYPE_SYSCLK | RCC_CLOCKTYPE_HCLK | RCC_CLOCKTYPE_PCLK1 | RCC_CLOCKTYPE_PCLK2);
    RCC_ClkInitStruct.ClockType |= (RCC_CLOCKTYPE_D3PCLK1 | RCC_CLOCKTYPE_D1PCLK1);
    RCC_ClkInitStruct.SYSCLKSource   = RCC_SYSCLKSOURCE_PLLCLK;
    RCC_ClkInitStruct.SYSCLKDivider  = RCC_SYSCLK_DIV1;
    RCC_ClkInitStruct.AHBCLKDivider  = RCC_HCLK_DIV2;
    RCC_ClkInitStruct.APB3CLKDivider = RCC_APB3_DIV2;
    RCC_ClkInitStruct.APB1CLKDivider = RCC_APB1_DIV2;
    RCC_ClkInitStruct.APB2CLKDivider = RCC_APB2_DIV2;
    RCC_ClkInitStruct.APB4CLKDivider = RCC_APB4_DIV2;

    PeriphClkInitStruct.PeriphClockSelection = RCC_PERIPHCLK_RTC | RCC_PERIPHCLK_USART2 | RCC_PERIPHCLK_RNG |
                                               RCC_PERIPHCLK_SPI123 | RCC_PERIPHCLK_SPI4 | RCC_PERIPHCLK_SDMMC |
                                               RCC_PERIPHCLK_I2C123 | RCC_PERIPHCLK_ADC | RCC_PERIPHCLK_I2C4 |
                                               RCC_PERIPHCLK_CKPER;
    PeriphClkInitStruct.PLL2.PLL2M      = 1;
    PeriphClkInitStruct.PLL2.PLL2N      = 18;
    PeriphClkInitStruct.PLL2.PLL2P      = 1;
    PeriphClkInitStruct.PLL2.PLL2Q      = 2;
    PeriphClkInitStruct.PLL2.PLL2R      = 2;
    PeriphClkInitStruct.PLL2.PLL2RGE    = RCC_PLL2VCIRANGE_3;
    PeriphClkInitStruct.PLL2.PLL2VCOSEL = RCC_PLL2VCOMEDIUM;
    PeriphClkInitStruct.PLL2.PLL2FRACN  = 6144;
#ifdef SCREEN_MODE_COLOR
    PeriphClkInitStruct.PLL3.PLL3M           = 1;     // 8 MHz input (HSE).
    PeriphClkInitStruct.PLL3.PLL3N           = 31;    // Multiply to 250 MHz (8 MHz * 31.25).
    PeriphClkInitStruct.PLL3.PLL3FRACN       = 2048;  // 0.25
    PeriphClkInitStruct.PLL3.PLL3P           = 4;     // 62.5 MHz (unused).
    PeriphClkInitStruct.PLL3.PLL3Q           = 2;     // 125 MHz (used for SPI123).
    PeriphClkInitStruct.PLL3.PLL3R           = 4;     // 62.5 MHz (unused).
    PeriphClkInitStruct.PLL3.PLL3RGE         = RCC_PLL2VCIRANGE_3;
    PeriphClkInitStruct.PLL3.PLL3VCOSEL      = RCC_PLL2VCOMEDIUM;
    PeriphClkInitStruct.Spi123ClockSelection = RCC_SPI123CLKSOURCE_PLL3;  // pll3_q_ck
#endif
#ifdef SCREEN_MODE_MONO
    PeriphClkInitStruct.Spi123ClockSelection = RCC_SPI123CLKSOURCE_PLL;                // pll1_q_ck
#endif                                                                                 // SCREEN_MODE_MONO
    PeriphClkInitStruct.CkperClockSelection       = RCC_CLKPSOURCE_HSE;                // per_ck = hse_ck = 8 MHz.
    PeriphClkInitStruct.SdmmcClockSelection       = RCC_SDMMCCLKSOURCE_PLL;            // pll1_q_ck
    PeriphClkInitStruct.Spi45ClockSelection       = RCC_SPI45CLKSOURCE_D2PCLK1;        // rcc_pclk
    PeriphClkInitStruct.Usart234578ClockSelection = RCC_USART234578CLKSOURCE_D2PCLK1;  // rcc_pclk
    PeriphClkInitStruct.RngClockSelection         = RCC_RNGCLKSOURCE_HSI48;            // hsi48_ck
    PeriphClkInitStruct.I2c123ClockSelection      = RCC_I2C123CLKSOURCE_D2PCLK1;       // rcc_pclk
    PeriphClkInitStruct.I2c4ClockSelection        = RCC_I2C4CLKSOURCE_D3PCLK1;         // rcc_pclk
    PeriphClkInitStruct.AdcClockSelection         = RCC_CLKPSOURCE_HSE;                // adc_ker_ck = per_ck = 8 MHz.
    PeriphClkInitStruct.RTCClockSelection         = RCC_RTCCLKSOURCE_LSI;              // lsi_ck

    if (enable) {
        RCC_OscInitStruct.PLL.PLLM = 1;
        RCC_OscInitStruct.PLL.PLLN = 120;
        RCC_OscInitStruct.PLL.PLLP = 2;
#ifdef SCREEN_MODE_COLOR
        RCC_OscInitStruct.PLL.PLLQ = 8;
#else  // SCREEN_MODE_MONO
        RCC_OscInitStruct.PLL.PLLQ = 120;
#endif
        RCC_OscInitStruct.PLL.PLLR = 2;
    } else {
        RCC_OscInitStruct.PLL.PLLM      = 1;
        RCC_OscInitStruct.PLL.PLLN      = 32;
        RCC_OscInitStruct.PLL.PLLP      = 2;
        RCC_OscInitStruct.PLL.PLLQ      = 32;
        RCC_OscInitStruct.PLL.PLLR      = 2;
        RCC_ClkInitStruct.SYSCLKDivider = RCC_SYSCLK_DIV2;
    }

    rc = HAL_RCC_OscConfig(&RCC_OscInitStruct);
    if (rc != HAL_OK) {
        // printf("[%s] HAL_RCC_OscConfig failed\n", __func__);
    }

    rc = HAL_RCCEx_PeriphCLKConfig(&PeriphClkInitStruct);
    if (rc != HAL_OK) {
        // printf("[%s] HAL_RCCEx_PeriphCLKConfig failed\n", __func__);
    }

    rc = HAL_RCC_ClockConfig(&RCC_ClkInitStruct, FLASH_LATENCY_4);
    if (rc != HAL_OK) {
        // printf("[%s] HAL_RCC_ClockConfig failed\n", __func__);
    }

    /* Adjust the backlight PWM based on the new frequency */
    backlight_adjust(enable);

#ifndef FACTORY_TEST
    /* Re-initialize the console UART based on the new frequency */
    frequency_update_console_uart();
#endif

    /* Re-initialize the SE UART based on the new frequency */
    se_setup();

    PLL3_ClocksTypeDef PLL3_Clocks = {0};
    HAL_RCCEx_GetPLL3ClockFreq(&PLL3_Clocks);

    printf("%lu, %lu, %lu, %lu, %lu, %lu\n", HAL_RCC_GetSysClockFreq(), SystemCoreClock, HAL_RCC_GetHCLKFreq(),
           HAL_RCC_GetPCLK1Freq(), HAL_RCC_GetPCLK2Freq(), PLL3_Clocks.PLL3_Q_Frequency);
}

void frequency_turbo(bool enable) {
    if (enable) {
        if (turbo_count == 0) {
            frequency_turbo_toggle(true);
        }
        turbo_count++;
    } else {
        if (turbo_count == 0) {
            // printf("ERROR: Tried to disable turbo mode when it was not already enabled!\n");
            return;
        }
        if (turbo_count == 1) {
            frequency_turbo_toggle(false);
        }
        turbo_count--;
    }
}
