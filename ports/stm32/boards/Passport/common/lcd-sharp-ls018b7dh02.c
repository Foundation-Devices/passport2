// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Screen driver for Sharp LS018B7DH02 monochrome display

#include <stdio.h>
#include <string.h>

#include "stm32h7xx_hal.h"

#include "lcd-sharp-ls018b7dh02.h"

#define LCD_NSS_PIN GPIO_PIN_15  // port A
#define LCD_SPI_SCK GPIO_PIN_5   // port A
#define LCD_SPI_MOSI GPIO_PIN_7  // port A

Screen                   screen;
static TIM_HandleTypeDef lcd_refresh_timer_handle;

uint8_t header_lookup[] = {
    0x80, 0x00, 0x81, 0x00, 0x80, 0x80, 0x81, 0x80, 0x80, 0x40, 0x81, 0x40, 0x80, 0xc0, 0x81, 0xc0, 0x80, 0x20, 0x81,
    0x20, 0x80, 0xa0, 0x81, 0xa0, 0x80, 0x60, 0x81, 0x60, 0x80, 0xe0, 0x81, 0xe0, 0x80, 0x10, 0x81, 0x10, 0x80, 0x90,
    0x81, 0x90, 0x80, 0x50, 0x81, 0x50, 0x80, 0xd0, 0x81, 0xd0, 0x80, 0x30, 0x81, 0x30, 0x80, 0xb0, 0x81, 0xb0, 0x80,
    0x70, 0x81, 0x70, 0x80, 0xf0, 0x81, 0xf0, 0x80, 0x08, 0x81, 0x08, 0x80, 0x88, 0x81, 0x88, 0x80, 0x48, 0x81, 0x48,
    0x80, 0xc8, 0x81, 0xc8, 0x80, 0x28, 0x81, 0x28, 0x80, 0xa8, 0x81, 0xa8, 0x80, 0x68, 0x81, 0x68, 0x80, 0xe8, 0x81,
    0xe8, 0x80, 0x18, 0x81, 0x18, 0x80, 0x98, 0x81, 0x98, 0x80, 0x58, 0x81, 0x58, 0x80, 0xd8, 0x81, 0xd8, 0x80, 0x38,
    0x81, 0x38, 0x80, 0xb8, 0x81, 0xb8, 0x80, 0x78, 0x81, 0x78, 0x80, 0xf8, 0x81, 0xf8, 0x80, 0x04, 0x81, 0x04, 0x80,
    0x84, 0x81, 0x84, 0x80, 0x44, 0x81, 0x44, 0x80, 0xc4, 0x81, 0xc4, 0x80, 0x24, 0x81, 0x24, 0x80, 0xa4, 0x81, 0xa4,
    0x80, 0x64, 0x81, 0x64, 0x80, 0xe4, 0x81, 0xe4, 0x80, 0x14, 0x81, 0x14, 0x80, 0x94, 0x81, 0x94, 0x80, 0x54, 0x81,
    0x54, 0x80, 0xd4, 0x81, 0xd4, 0x80, 0x34, 0x81, 0x34, 0x80, 0xb4, 0x81, 0xb4, 0x80, 0x74, 0x81, 0x74, 0x80, 0xf4,
    0x81, 0xf4, 0x80, 0x0c, 0x81, 0x0c, 0x80, 0x8c, 0x81, 0x8c, 0x80, 0x4c, 0x81, 0x4c, 0x80, 0xcc, 0x81, 0xcc, 0x80,
    0x2c, 0x81, 0x2c, 0x80, 0xac, 0x81, 0xac, 0x80, 0x6c, 0x81, 0x6c, 0x80, 0xec, 0x81, 0xec, 0x80, 0x1c, 0x81, 0x1c,
    0x80, 0x9c, 0x81, 0x9c, 0x80, 0x5c, 0x81, 0x5c, 0x80, 0xdc, 0x81, 0xdc, 0x80, 0x3c, 0x81, 0x3c, 0x80, 0xbc, 0x81,
    0xbc, 0x80, 0x7c, 0x81, 0x7c, 0x80, 0xfc, 0x81, 0xfc, 0x80, 0x02, 0x81, 0x02, 0x80, 0x82, 0x81, 0x82, 0x80, 0x42,
    0x81, 0x42, 0x80, 0xc2, 0x81, 0xc2, 0x80, 0x22, 0x81, 0x22, 0x80, 0xa2, 0x81, 0xa2, 0x80, 0x62, 0x81, 0x62, 0x80,
    0xe2, 0x81, 0xe2, 0x80, 0x12, 0x81, 0x12, 0x80, 0x92, 0x81, 0x92, 0x80, 0x52, 0x81, 0x52, 0x80, 0xd2, 0x81, 0xd2,
    0x80, 0x32, 0x81, 0x32, 0x80, 0xb2, 0x81, 0xb2, 0x80, 0x72, 0x81, 0x72, 0x80, 0xf2, 0x81, 0xf2, 0x80, 0x0a, 0x81,
    0x0a, 0x80, 0x8a, 0x81, 0x8a, 0x80, 0x4a, 0x81, 0x4a, 0x80, 0xca, 0x81, 0xca, 0x80, 0x2a, 0x81, 0x2a, 0x80, 0xaa,
    0x81, 0xaa, 0x80, 0x6a, 0x81, 0x6a, 0x80, 0xea, 0x81, 0xea, 0x80, 0x1a, 0x81, 0x1a, 0x80, 0x9a, 0x81, 0x9a, 0x80,
    0x5a, 0x81, 0x5a, 0x80, 0xda, 0x81, 0xda, 0x80, 0x3a, 0x81, 0x3a, 0x80, 0xba, 0x81, 0xba, 0x80, 0x7a, 0x81, 0x7a,
    0x80, 0xfa, 0x81, 0xfa, 0x80, 0x06, 0x81, 0x06, 0x80, 0x86, 0x81, 0x86, 0x80, 0x46, 0x81, 0x46, 0x80, 0xc6, 0x81,
    0xc6, 0x80, 0x26, 0x81, 0x26, 0x80, 0xa6, 0x81, 0xa6, 0x80, 0x66, 0x81, 0x66, 0x80, 0xe6, 0x81, 0xe6, 0x80, 0x16,
    0x81, 0x16, 0x80, 0x96, 0x81, 0x96, 0x80, 0x56, 0x81, 0x56, 0x80, 0xd6, 0x81, 0xd6, 0x80, 0x36, 0x81, 0x36, 0x80,
    0xb6, 0x81, 0xb6, 0x80, 0x76, 0x81, 0x76, 0x80, 0xf6, 0x81, 0xf6, 0x80, 0x0e, 0x81, 0x0e, 0x80, 0x8e, 0x81, 0x8e,
    0x80, 0x4e, 0x81, 0x4e, 0x80, 0xce, 0x81, 0xce, 0x80, 0x2e, 0x81, 0x2e, 0x80, 0xae, 0x81, 0xae, 0x80, 0x6e, 0x81,
    0x6e, 0x80, 0xee, 0x81, 0xee, 0x80, 0x1e, 0x81, 0x1e, 0x80, 0x9e, 0x81, 0x9e, 0x80, 0x5e, 0x81, 0x5e, 0x80, 0xde,
    0x81, 0xde, 0x80, 0x3e, 0x81, 0x3e, 0x80, 0xbe, 0x81, 0xbe, 0x80, 0x7e, 0x81, 0x7e, 0x80, 0xfe, 0x81, 0xfe, 0x80,
    0x01, 0x81, 0x01, 0x80, 0x81, 0x81, 0x81, 0x80, 0x41, 0x81, 0x41, 0x80, 0xc1, 0x81, 0xc1, 0x80, 0x21, 0x81, 0x21,
    0x80, 0xa1, 0x81, 0xa1, 0x80, 0x61, 0x81, 0x61, 0x80, 0xe1, 0x81, 0xe1, 0x80, 0x11, 0x81, 0x11, 0x80, 0x91, 0x81,
    0x91, 0x80, 0x51, 0x81, 0x51, 0x80, 0xd1, 0x81, 0xd1, 0x80, 0x31, 0x81, 0x31, 0x80, 0xb1, 0x81, 0xb1, 0x80, 0x71,
    0x81, 0x71, 0x80, 0xf1, 0x81, 0xf1, 0x80, 0x09, 0x81, 0x09, 0x80, 0x89, 0x81, 0x89, 0x80, 0x49, 0x81, 0x49, 0x80,
    0xc9, 0x81, 0xc9, 0x80, 0x29, 0x81, 0x29, 0x80, 0xa9, 0x81, 0xa9, 0x80, 0x69, 0x81, 0x69, 0x80, 0xe9};

typedef struct {
    SPI_HandleTypeDef* spi;
    int                row;
    int                column;
} lcd_t;

static lcd_t             lcd;
static SPI_HandleTypeDef spi_port;

void lcd_fill(uint16_t color) {
    for (uint32_t y = 0; y < SCREEN_HEIGHT; y++) {
        for (uint32_t x = 0; x < SCREEN_HEIGHT; x++) {
            lcd_set_pixel(x, y, color);
        }
    }
}

void lcd_clear(uint16_t color) {
    uint8_t invert_mask  = color == COLOR_WHITE ? 0x40 : 0x00;
    uint8_t clear_msg[2] = {0x20 | invert_mask, 0x00};

    HAL_SPI_Transmit(lcd.spi, clear_msg, 2, 1000);
}

void lcd_init(bool clear) {
    SPI_InitTypeDef*        init;
    TIM_MasterConfigTypeDef sMasterConfig   = {0};
    TIM_OC_InitTypeDef      sConfigOC       = {0};
    GPIO_InitTypeDef        GPIO_InitStruct = {0};

    __HAL_RCC_GPIOA_CLK_ENABLE();
    __HAL_RCC_GPIOE_CLK_ENABLE();
    __HAL_RCC_SPI1_CLK_ENABLE();

    GPIO_InitStruct.Pin       = LCD_NSS_PIN;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = LCD_SPI_SCK;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    GPIO_InitStruct.Pin       = LCD_SPI_MOSI;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_PULLUP;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_HIGH;
    GPIO_InitStruct.Alternate = GPIO_AF5_SPI1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    lcd.spi           = &spi_port;
    lcd.spi->Instance = SPI1;
    init              = &lcd.spi->Init;

    // init the SPI bus
    init->Mode = SPI_MODE_MASTER;

    //
    // These configuration values are from the IDE
    // test code.
    //
    init->BaudRatePrescaler = SPI_BAUDRATEPRESCALER_4;
    init->CLKPolarity       = SPI_POLARITY_HIGH;
    init->CLKPhase          = SPI_PHASE_1EDGE;
    init->Direction         = SPI_DIRECTION_2LINES_TXONLY;
    init->DataSize          = SPI_DATASIZE_8BIT;
    init->NSS               = SPI_NSS_HARD_OUTPUT;  // SPI_NSS_SOFT;
    init->FirstBit          = SPI_FIRSTBIT_MSB;
    init->TIMode            = SPI_TIMODE_DISABLED;
    init->CRCCalculation    = SPI_CRCCALCULATION_DISABLED;
    init->CRCPolynomial     = 0;

    // === These are in the cubeIDE init code but not the MP LCD module make_new init code
    init->NSSPMode                   = SPI_NSS_PULSE_ENABLE;
    init->NSSPolarity                = SPI_NSS_POLARITY_HIGH;
    init->FifoThreshold              = SPI_FIFO_THRESHOLD_01DATA;
    init->TxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    init->RxCRCInitializationPattern = SPI_CRC_INITIALIZATION_ALL_ZERO_PATTERN;
    init->MasterSSIdleness           = SPI_MASTER_SS_IDLENESS_01CYCLE;
    init->MasterInterDataIdleness    = SPI_MASTER_INTERDATA_IDLENESS_00CYCLE;
    init->MasterReceiverAutoSusp     = SPI_MASTER_RX_AUTOSUSP_DISABLE;
    init->MasterKeepIOState          = SPI_MASTER_KEEP_IO_STATE_DISABLE;
    init->IOSwap                     = SPI_IO_SWAP_DISABLE;

    HAL_SPI_Init(lcd.spi);

    // Code to configure Timer 1 using code similar to the MP LED module PWM timer code.
    __TIM1_CLK_ENABLE();

    lcd_refresh_timer_handle.Instance               = TIM1;
    lcd_refresh_timer_handle.Init.Prescaler         = 128;  // TIM runs at 1MHz
    lcd_refresh_timer_handle.Init.CounterMode       = TIM_COUNTERMODE_UP;
    lcd_refresh_timer_handle.Init.Period            = 65535;
    lcd_refresh_timer_handle.Init.ClockDivision     = TIM_CLOCKDIVISION_DIV1;
    lcd_refresh_timer_handle.Init.RepetitionCounter = 0;
    lcd_refresh_timer_handle.Init.AutoReloadPreload = TIM_AUTORELOAD_PRELOAD_DISABLE;
    HAL_TIM_PWM_Init(&lcd_refresh_timer_handle);

    sMasterConfig.MasterOutputTrigger  = TIM_TRGO_RESET;
    sMasterConfig.MasterOutputTrigger2 = TIM_TRGO2_RESET;
    sMasterConfig.MasterSlaveMode      = TIM_MASTERSLAVEMODE_DISABLE;
    HAL_TIMEx_MasterConfigSynchronization(&lcd_refresh_timer_handle, &sMasterConfig);

    // PWM configuration
    sConfigOC.OCMode       = TIM_OCMODE_PWM1;
    sConfigOC.Pulse        = 32768;
    sConfigOC.OCPolarity   = TIM_OCPOLARITY_HIGH;
    sConfigOC.OCNPolarity  = TIM_OCNPOLARITY_HIGH;
    sConfigOC.OCFastMode   = TIM_OCFAST_DISABLE;
    sConfigOC.OCIdleState  = TIM_OCIDLESTATE_RESET;
    sConfigOC.OCNIdleState = TIM_OCNIDLESTATE_RESET;
    HAL_TIM_PWM_ConfigChannel(&lcd_refresh_timer_handle, &sConfigOC, TIM_CHANNEL_1);

    GPIO_InitStruct.Pin       = GPIO_PIN_8;
    GPIO_InitStruct.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStruct.Pull      = GPIO_NOPULL;
    GPIO_InitStruct.Speed     = GPIO_SPEED_FREQ_LOW;
    GPIO_InitStruct.Alternate = GPIO_AF1_TIM1;
    HAL_GPIO_Init(GPIOA, &GPIO_InitStruct);

    // Start timer to refresh the SRAM inside the LCD
    HAL_TIM_PWM_Start(&lcd_refresh_timer_handle, TIM_CHANNEL_1);

    // Initialize header bytes once
    for (int y = 0; y < SCREEN_HEIGHT; y++) {
        // Use lookup table to set header bytes
        screen.lines[y].header[0] = header_lookup[y * 2];
        screen.lines[y].header[1] = header_lookup[y * 2 + 1];
    }

    if (clear) {
        lcd_clear(COLOR_WHITE);
    }
}

void lcd_deinit(void) {
    __HAL_RCC_SPI1_FORCE_RESET();
    __HAL_RCC_SPI1_RELEASE_RESET();
    __HAL_RCC_SPI1_CLK_DISABLE();
}

void lcd_update(bool invert) {
    // Write the screen data to the screen all at once -- this is much
    // faster than separate writes for each line
    HAL_SPI_Transmit(lcd.spi, (uint8_t*)&screen, sizeof(screen), 1000);
}

void lcd_draw_glyph(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* glyph, uint16_t color) {
    for (uint32_t cy = 0; cy < h; cy++) {
        for (uint32_t cx = 0; cx < w; cx++) {
            uint16_t color = lcd_get_image_pixel(cx, cy, w, h, glyph, COLOR_WHITE);
            if (color == COLOR_BLACK) {
                lcd_set_pixel(x + cx, y + cy, color);
            }
        }
    }
}

void lcd_update_rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* data) {
    // printf("lcd_update_rect(): x=%u, y=%u w=%u h=%u &screen=0x%08lx\n", x, y, w, h, &screen);
    for (uint16_t cy = 0; cy < h; cy++) {
        memcpy(screen.lines[y + cy].pixels, &data[cy * SCREEN_BYTES_PER_LINE], SCREEN_BYTES_PER_LINE);
    }

    // Send the lines all at once
    HAL_SPI_Transmit(lcd.spi, (uint8_t*)&screen.lines[y], sizeof(ScreenLine) * h, 1000);
}

#define VIEWFINDER_WIDTH 188
#define VIEWFINDER_HEIGHT 188
#define VIEWFINDER_Y_START 49
#define VIEWFINDER_X_OFFSET (SCREEN_WIDTH - VIEWFINDER_WIDTH) / 2

// Force the specified pixel to white
static void _lcd_set_pixel(uint32_t x, uint32_t y) {
    uint32_t mono_offset = x >> 3;
    uint8_t  bit         = x % 8;
    uint8_t* p_byte      = &screen.lines[y].pixels[mono_offset];

    // Set the bit
    *p_byte |= 1 << (7 - bit);
}

// A very hard-coded function to resize the grayscale camera image to the viewfinder size, and convert from
// grayscale to mono as quickly as possible.
static void _lcd_resize_and_render_viewfinder_direct(uint8_t* grayscale, uint32_t gray_hor_res, uint32_t gray_ver_res) {
    float scale = (float)gray_ver_res / (float)VIEWFINDER_HEIGHT;

    // printf("hor_res=%lu ver_res=%lu scale=%f\n", gray_hor_res, gray_ver_res, (double)scale);

    for (uint32_t y = 0; y < VIEWFINDER_HEIGHT; y++) {
        for (uint32_t x = 0; x < VIEWFINDER_WIDTH; x++) {
            uint32_t offset = ((uint32_t)((float)(x)*scale) * (uint32_t)gray_hor_res) + (uint32_t)((float)(y)*scale);
            uint8_t  gray   = grayscale[offset];

            // Mask the value in it
            uint32_t flipped_x   = VIEWFINDER_WIDTH - x;
            uint32_t mono_offset = (VIEWFINDER_X_OFFSET + flipped_x) >> 3;
            uint8_t  bit         = (VIEWFINDER_X_OFFSET + flipped_x) % 8;
            uint8_t* p_byte      = &screen.lines[VIEWFINDER_Y_START + y].pixels[mono_offset];

            if (gray > 64) {
                // Set the bit
                *p_byte |= 1 << (7 - bit);
            } else {
                // Clear the bit
                *p_byte &= ~(1 << (7 - bit));
            }
        }
    }

    // Force the corners to be white to "round" the viewfinder
    uint32_t corner_lines[] = {8, 6, 5, 3, 3, 2, 1, 1};
    uint32_t num_lines      = sizeof(corner_lines) / sizeof(uint32_t);
    for (uint32_t x = 0; x < num_lines; x++) {
        for (uint32_t y = 0; y < corner_lines[x]; y++) {
            // Upper-left
            _lcd_set_pixel(VIEWFINDER_X_OFFSET + x, VIEWFINDER_Y_START + y);

            // Upper-right
            _lcd_set_pixel(VIEWFINDER_X_OFFSET + VIEWFINDER_WIDTH - x, VIEWFINDER_Y_START + y);

            // Lower-left
            _lcd_set_pixel(VIEWFINDER_X_OFFSET + x, VIEWFINDER_Y_START + VIEWFINDER_HEIGHT - y);

            // Lower-right
            _lcd_set_pixel(VIEWFINDER_X_OFFSET + VIEWFINDER_WIDTH - x, VIEWFINDER_Y_START + VIEWFINDER_HEIGHT - y);
        }
    }
}

// Given a full grayscale camera image buffer, resize it to fit in a
void lcd_update_viewfinder(uint8_t* grayscale, uint16_t gray_hor_res, uint16_t gray_ver_res) {
    // Grayscale buffer is 396*330 pixels, and we need to scale down to 180x180 size of the viewfiender,
    // and position it at the right place on the display, then write the corresponding lines.
    _lcd_resize_and_render_viewfinder_direct(grayscale, gray_hor_res, gray_ver_res);

    // Send the lines of the viewfinder to the display
    HAL_SPI_Transmit(lcd.spi, (uint8_t*)&screen.lines[VIEWFINDER_Y_START], sizeof(ScreenLine) * VIEWFINDER_HEIGHT,
                     1000);
}

void lcd_draw_image(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* image) {
    for (uint32_t cy = 0; cy < h; cy++) {
        for (uint32_t cx = 0; cx < w; cx++) {
            uint32_t color = lcd_get_image_pixel(cx, cy, w, h, image, COLOR_WHITE);
            lcd_set_pixel(x + cx, y + cy, color);
        }
    }
}

uint16_t lcd_get_glyph_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* glyph) {
    return lcd_get_image_pixel(x, y, w, h, glyph, COLOR_BLACK);
}

uint16_t lcd_get_image_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* image, uint16_t default_color) {
    if (x < 0 || x >= w || y < 0 || y >= h) {
        return default_color;
    }

    uint16_t w_bytes = (w + 7) / 8;
    uint16_t offset  = (y * w_bytes) + x / 8;
    uint8_t  bit     = 1 << (7 - x % 8);

    // We flip the color meanings here for images!
    return ((image[offset] & bit) == 0) ? COLOR_WHITE : COLOR_BLACK;
}

void lcd_set_pixel(int16_t x, int16_t y, uint16_t color) {
    if (x < 0 || x >= SCREEN_WIDTH || y < 0 || y >= SCREEN_HEIGHT) {
        return;
    }

    uint8_t* line   = screen.lines[y].pixels;
    uint16_t offset = x / 8;
    uint8_t  bit    = 1 << (7 - x % 8);
    if (color == COLOR_BLACK) {
        line[offset] &= ~bit;
    } else {
        line[offset] |= bit;
    }
}
