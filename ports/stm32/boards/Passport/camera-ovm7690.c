// SPDX-FileCopyrightText: © 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: BSD-3-Clause

/*-----------------------------------------------------------------------------
 * Copyright (c) 2013 - 2018 Arm Limited (or its affiliates). All
 * rights reserved.
 *
 * SPDX-License-Identifier: BSD-3-Clause
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *   1.Redistributions of source code must retain the above copyright
 *     notice, this list of conditions and the following disclaimer.
 *   2.Redistributions in binary form must reproduce the above copyright
 *     notice, this list of conditions and the following disclaimer in the
 *     documentation and/or other materials provided with the distribution.
 *   3.Neither the name of Arm nor the names of its contributors may be used
 *     to endorse or promote products derived from this softwarwe without
 *     specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
 * AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
 * ARE DISCLAIMED. IN NO EVENT SHALL COPYRIGHT HOLDERS AND CONTRIBUTORS BE
 * LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
 * CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
 * SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
 * INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
 * CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
 * ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
 * POSSIBILITY OF SUCH DAMAGE.
 *-----------------------------------------------------------------------------
 * Name:    Camera_OVM7690.c
 * Purpose: Digital camera OVM7690 interface
 * Rev.:    1.0.0
 *----------------------------------------------------------------------------*/

#include <stdio.h>
#include <string.h>

#include "stm32h7xx_hal.h"

#include "camera-ovm7690.h"
#include "dma.h"

#define CAMERA_I2C_ADDR (0x21 << 1)  // Use 8-bit address

typedef struct {
    uint8_t addr;
    uint8_t val;
} camera_reg_t;

/* OmniVision recommended settings based on OVM7690 Setting V2.2              */
/* Modified for RGB QVGA settings                                             */
static camera_reg_t _camera_reg_init[] = {
    // OV7690 396x330 30ps_RGB565 (60hz)
    // Sensor   : OVM7690

#if SCREEN_MODE_MONO
    {REG0C, 0x96},
#elif SCREEN_MODE_COLOR
    // Flip and invert the image due to the camera orientation on the board
    {REG0C, 0xD6},
#endif

    {REG81, 0xff},
    {AECGM, 0x23},
    {REG16, 0x03},
    {0x39, 0x80},
    {0x1e, 0xb1},

    //===Format===
    {REG12, 0x06},
    {REG82, 0x03},
    {REGD0, 0x48},
    {REG80, 0x7f},
    {REG3E, 0x30},
    {REG22, 0x00},

    //===Resolution===
    {HSIZE, 0xa4},
    {VSIZE, 0xf6},

    //===Zoom===
    {REGC8, 0x02},
    {REGC9, 0x40},  // ISP input hsize (576)
    {REGCA, 0x01},
    {REGCB, 0xe0},  // ISP input vsize (480)

    {REGCC, 0x01},
    {REGCD, 0x8c},  // ISP output hsize (396)
    {REGCE, 0x01},
    {REGCF, 0x4a},  // ISP output vsize (330)

    //===Position===
    {HSTART, 0x69},  // h
    {VSTART, 0x0C},  // v

    //===Lens Correction==
    {LCC0, 0x90},
    {LCC1, 0x00},
    {LCC2, 0x00},
    {LCC3, 0x10},
    {LCC4, 0x30},
    {LCC5, 0x29},
    {LCC6, 0x26},

    //====Color Matrix====
    {REGBB, 0x80},
    {REGBC, 0x62},
    {REGBD, 0x1e},
    {REGBE, 0x26},
    {REGBF, 0x7b},
    {REGC0, 0xac},
    {REGC1, 0x1e},

    //===Edge + Denoise====
    {REGB7, 0x05},
    {REGB8, 0x09},
    {REGB9, 0x00},
    {REGBA, 0x18},

    //===UVAdjust====
    {UVCTR0, 0x4A},
    {UVCTR1, 0x9F},
    {UVCTR2, 0x48},
    {UVCTR3, 0x32},

    //====AEC/AGC target====
    {WPT, 0x78},
    {BPT, 0x68},
    {VPT, 0xb3},

    //====Gamma====
    {GAM1, 0x0b},
    {GAM2, 0x15},
    {GAM3, 0x2a},
    {GAM4, 0x51},
    {GAM5, 0x63},
    {GAM6, 0x74},
    {GAM7, 0x83},
    {GAM8, 0x91},
    {GAM9, 0x9e},
    {GAM10, 0xaa},
    {GAM11, 0xbe},
    {GAM12, 0xce},
    {GAM13, 0xe5},
    {GAM14, 0xf3},
    {GAM15, 0xfb},
    {SLOPE, 0x06},

    //===AWB===
    //==Advanced==
    {0x8c, 0x5d},
    {0x8d, 0x11},
    {0x8e, 0x12},
    {0x8f, 0x11},
    {0x90, 0x50},
    {0x91, 0x22},
    {0x92, 0xd1},
    {0x93, 0xa7},
    {0x94, 0x23},
    {0x95, 0x3b},
    {0x96, 0xff},
    {0x97, 0x00},
    {0x98, 0x4a},
    {0x99, 0x46},
    {0x9a, 0x3d},
    {0x9b, 0x3a},
    {0x9c, 0xf0},
    {0x9d, 0xf0},
    {0x9e, 0xf0},
    {0x9f, 0xff},
    {0xa0, 0x56},
    {0xa1, 0x55},
    {0xa2, 0x13},

    //==General Control==
    {BD50ST, 0x9a},
    {BD60ST, 0x80},

    {REG14, 0x29},
    {REG13, 0xe7},
    {CLKRC, 0x40},  // Changed from 0 - we use an external oscillator
};
#define CAMERA_REG_INIT_NUMOF (sizeof(_camera_reg_init) / sizeof(camera_reg_t))

static DMA_HandleTypeDef  hdma;
static DCMI_HandleTypeDef hdcmi;
static I2C_HandleTypeDef  hi2c1;
static TIM_HandleTypeDef  tim3;

static HAL_StatusTypeDef _camera_read(uint8_t reg, uint8_t* data) {
    HAL_StatusTypeDef ret = HAL_OK;

    if ((ret = HAL_I2C_Master_Transmit(&hi2c1, CAMERA_I2C_ADDR, &reg, 1, 100)) != HAL_OK) {
        // printf("[%s] HAL_I2C_Master_Transmit() failed\n", __func__);
        return ret;
    }

    if ((ret = HAL_I2C_Master_Receive(&hi2c1, CAMERA_I2C_ADDR, data, 1, 100)) != HAL_OK) {
        // printf("[%s] HAL_I2C_Master_Receive() failed\n", __func__);
        return ret;
    }

    return HAL_OK;
}

static HAL_StatusTypeDef _camera_write(uint8_t reg, uint8_t data) {
    HAL_StatusTypeDef ret = HAL_OK;

    if ((ret = HAL_I2C_Mem_Write(&hi2c1, CAMERA_I2C_ADDR, reg, I2C_MEMADD_SIZE_8BIT, &data, 1, 100)) != HAL_OK) {
        // printf("[%s] HAL_I2C_Mem_Write() failed\n", __func__);
        return ret;
    }

    return HAL_OK;
}

static HAL_StatusTypeDef _camera_set_qvga(void) {
    HAL_StatusTypeDef ret = HAL_OK;

    for (int i = 0; i < CAMERA_REG_INIT_NUMOF; i++) {
        if ((ret = _camera_write(_camera_reg_init[i].addr, _camera_reg_init[i].val)) != HAL_OK) {
            // printf("[%s] _camera_write() failed on index %d\n", __func__, i);
            return ret;
        }
    }

    return HAL_OK;
}

static void _camera_dcmi_clear_int(void) {
    hdcmi.Instance->ICR = DCMI_IT_FRAME | DCMI_IT_OVR | DCMI_IT_ERR | DCMI_IT_VSYNC | DCMI_IT_LINE;
}

HAL_StatusTypeDef _camera_dcmi_stop(void) {
    HAL_StatusTypeDef ret = HAL_OK;

    if ((ret = HAL_DCMI_Stop(&hdcmi)) != HAL_OK) {
        // printf("[%s] HAL_DCMI_Stop() failed\n", __func__);
        return ret;
    }

    return HAL_OK;
}

HAL_StatusTypeDef camera_init(void) {
    HAL_StatusTypeDef       ret                = HAL_OK;
    GPIO_InitTypeDef        GPIO_InitStruct    = {0};
    TIM_MasterConfigTypeDef tim3_master_config = {0};
    TIM_OC_InitTypeDef      tim3_pwm_config    = {0};
    uint16_t                Period             = (SystemCoreClock / 24000000); /* Need 24 MHz clock for the camera */
    uint8_t                 val                = 0;

    /* Per STM Appnote AN5020
     * Reset DCMI by setting bit in RCC_AHB2RSTR register to reset clock domains
     * Configure GPIOs
     * Configure timings and clocks (done at startup)
     * Configure DCMI
     * Configure DMA
     * Configure Camera module
     */

    /* PE7 DCMI_PWDN config set before pinmux */
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, GPIO_PIN_RESET);

    /* DCMI_PWDN pin PE7 PE8 PWR_EN */
    GPIO_InitStruct.Pin   = GPIO_PIN_7 | GPIO_PIN_8;
    GPIO_InitStruct.Mode  = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull  = GPIO_NOPULL;
    GPIO_InitStruct.Speed = GPIO_SPEED_FREQ_LOW;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* DCMI pin setup */
    GPIO_InitStruct.Pin       = GPIO_PIN_4 | GPIO_PIN_6;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF13_DCMI;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_7;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF13_DCMI;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_6 | GPIO_PIN_7;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF13_DCMI;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_3;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF13_DCMI;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = GPIO_PIN_0 | GPIO_PIN_1 | GPIO_PIN_4 | GPIO_PIN_5 | GPIO_PIN_6;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF13_DCMI;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* TIM3 GPIO Configuration: PB1 -> TIM3_CH4 */
    GPIO_InitStruct.Pin       = GPIO_PIN_1;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF2_TIM3;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* I2C1 Pin configuration */
    GPIO_InitStruct.Pin       = GPIO_PIN_6 | GPIO_PIN_9;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_OD;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF4_I2C1;
    HAL_GPIO_Init(GPIOB, &GPIO_InitStruct);

    /* Configure the BUF1_OE and BUF2_OE */
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_9, 0);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_10, 0);

    GPIO_InitStruct.Pin       = GPIO_PIN_9 | GPIO_PIN_10;
    GPIO_InitStruct.Mode      = GPIO_MODE_OUTPUT_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = 0;
    HAL_GPIO_Init(GPIOE, &GPIO_InitStruct);

    /* Configure Timer 3 channel 4 */
    __TIM3_CLK_ENABLE();

    tim3.Instance               = TIM3;
    tim3.Init.Prescaler         = 0;
    tim3.Init.CounterMode       = TIM_COUNTERMODE_UP;
    tim3.Init.Period            = Period - 1;
    tim3.Init.ClockDivision     = 0;
    tim3.Init.RepetitionCounter = 0;
    tim3.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    if ((ret = HAL_TIM_PWM_Init(&tim3)) != HAL_OK) {
        // printf("[%s] HAL_TIM_PWM_Init() failed\n", __func__);
        return ret;
    }

    tim3_master_config.MasterOutputTrigger = TIM_TRGO_RESET;
    tim3_master_config.MasterSlaveMode     = TIM_MASTERSLAVEMODE_DISABLE;
    if ((ret = HAL_TIMEx_MasterConfigSynchronization(&tim3, &tim3_master_config)) != HAL_OK) {
        // printf("[%s] HAL_TIMEx_MasterConfigSynchronization() failed\n", __func__);
        return ret;
    }

    /* PWM configuration */
    tim3_pwm_config.OCMode     = TIM_OCMODE_PWM1;
    tim3_pwm_config.Pulse      = Period / 2;
    tim3_pwm_config.OCPolarity = TIM_OCPOLARITY_HIGH;
    tim3_pwm_config.OCFastMode = TIM_OCFAST_DISABLE;
    if ((ret = HAL_TIM_PWM_ConfigChannel(&tim3, &tim3_pwm_config, TIM_CHANNEL_4)) != HAL_OK) {
        // printf("[%s] HAL_TIM_PWM_ConfigChannel() failed\n", __func__);
        return ret;
    }
    HAL_TIM_PWM_Start(&tim3, TIM_CHANNEL_4);

    /* I2C1 config */
    __HAL_RCC_I2C1_CLK_ENABLE();
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
    if ((ret = HAL_I2C_Init(&hi2c1)) != HAL_OK) {
        // printf("[%s] HAL_I2C_Init() failed\n", __func__);
        return ret;
    }

    /* Reset DCMI */
    __DCMI_CLK_ENABLE();
    __HAL_RCC_DCMI_FORCE_RESET();
    HAL_Delay(20);
    __HAL_RCC_DCMI_RELEASE_RESET();

    /* Configure DCMI peripheral */
    hdcmi.Instance              = DCMI;
    hdcmi.Init.SynchroMode      = DCMI_SYNCHRO_HARDWARE;
    hdcmi.Init.PCKPolarity      = DCMI_PCKPOLARITY_RISING;
    hdcmi.Init.VSPolarity       = DCMI_VSPOLARITY_HIGH;
    hdcmi.Init.HSPolarity       = DCMI_HSPOLARITY_LOW;
    hdcmi.Init.CaptureRate      = DCMI_CR_ALL_FRAME;
    hdcmi.Init.ExtendedDataMode = DCMI_EXTEND_DATA_8B;
    hdcmi.Init.JPEGMode         = DCMI_JPEG_DISABLE;
    if ((ret = HAL_DCMI_Init(&hdcmi)) != HAL_OK) {
        // printf("[%s] HAL_DCMI_Init() failed\n", __func__);
        return ret;
    }

    /* DMA configuration */
    dma_init(&hdma, &dma_DCMI_0, DMA_PERIPH_TO_MEMORY, &hdcmi);
    __HAL_LINKDMA(&hdcmi, DMA_Handle, hdma);

    /* Reset camera, power down pin is active high */
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, GPIO_PIN_SET);
    HAL_Delay(20);
    HAL_GPIO_WritePin(GPIOE, GPIO_PIN_7, GPIO_PIN_RESET);
    HAL_Delay(20);

    /* Configure camera size, color mode, etc. */
    _camera_set_qvga();

    /* Don't reset camera sensor timing when mode changes. */
    if ((ret = _camera_read(0x6F, &val)) != HAL_OK) {
        // printf("[%s] _camera_read() failed\n", __func__);
        return ret;
    }
    val &= ~(1 << 7);
    if ((ret = _camera_write(0x6F, val)) != HAL_OK) {
        // printf("[%s] _camera_read() failed\n", __func__);
        return ret;
    }

    // printf("[%s] CAMERA INIT COMPLETE!\n", __func__);
    return HAL_OK;
}

HAL_StatusTypeDef camera_on(void) {
    HAL_StatusTypeDef ret = HAL_OK;
    uint8_t           val = 0;

    if ((ret = _camera_read(0x0E, &val)) < 0) {
        // printf("[%s] _camera_read() failed\n", __func__);
        return ret;
    }
    val &= ~(1 << 3);
    if ((ret = _camera_write(0x0E, val)) < 0) {
        // printf("[%s] _camera_write() failed\n", __func__);
        return ret;
    }

    return HAL_OK;
}

HAL_StatusTypeDef camera_off(void) {
    HAL_StatusTypeDef ret = HAL_OK;
    uint8_t           val = 0;

    if ((ret = HAL_DCMI_Stop(&hdcmi)) != HAL_OK) {
        // printf("[%s] HAL_DCMI_Stop() failed\n", __func__);
        return ret;
    }

    if ((ret = _camera_read(0x0E, &val)) < 0) {
        // printf("[%s] _camera_read() failed\n", __func__);
        return ret;
    }

    /* Put camera into sleep mode. */
    if ((ret = _camera_write(0x0E, val | (1 << 3))) < 0) {
        // printf("[%s] _camera_write() failed\n", __func__);
        return ret;
    }

    return HAL_OK;
}

HAL_StatusTypeDef camera_snapshot(void) {
    HAL_StatusTypeDef ret              = HAL_OK;
    uint16_t*         framebuffer_addr = NULL;

    if ((framebuffer_addr = framebuffer_camera()) == NULL) {
        // printf("[%s] framebuffer_camera() failed\n", __func__);
        return HAL_ERROR;
    }

    // uint32_t total_start = HAL_GetTick();
    // uint32_t total_end = 0;

    // Clear any current interrupts
    _camera_dcmi_clear_int();

    /* Take a snapshot */
    if ((ret = HAL_DCMI_Start_DMA(&hdcmi, DCMI_MODE_SNAPSHOT, (uint32_t)framebuffer_addr,
                                  CAMERA_FRAMEBUFFER_SIZE / 4)) != HAL_OK) {
        // printf("[%s] HAL_DCMI_Start_DMA() failed\n", __func__);
        return ret;
    }

    /* Poll for frame completion */
    uint16_t count = 0;
    while (!(hdcmi.Instance->RISR & DCMI_IT_FRAME)) {
        HAL_Delay(1);
        ++count;
        if (count > 1000) {
            // printf("[%s] frame complete did not occur in 1 second\n", __func__);
            if ((ret = HAL_DCMI_Stop(&hdcmi)) != HAL_OK) {
                // printf("[%s] HAL_DCMI_Stop() failed\n", __func__);
                return ret;
            }
            return HAL_TIMEOUT;
        }
    }
    // printf("[%s] frame complete in %d milliseconds\n", __func__, count);

    if ((ret = HAL_DCMI_Stop(&hdcmi)) != HAL_OK) {
        // printf("[%s] HAL_DCMI_Stop() failed\n", __func__);
        return ret;
    }

    // total_end = HAL_GetTick();
    // printf("camera_snapshot(): took %lu ms\n", total_end - total_start);
    return HAL_OK;
}
