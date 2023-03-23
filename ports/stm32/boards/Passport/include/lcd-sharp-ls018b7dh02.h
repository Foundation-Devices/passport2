// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// LCD driver for Sharp LS018B7DH02 monochrome display

#ifndef __LCD_SHARP_H__
#define __LCD_SHARP_H__

#include "stm32h7xx_hal.h"

#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>

#define SCREEN_WIDTH 230
#define SCREEN_HEIGHT 303
#define SCREEN_BUFFER_WIDTH 240
#define SCREEN_BITS_PER_PIXEL 1

#define SCREEN_BYTES_PER_LINE (SCREEN_BUFFER_WIDTH / 8)

// TODO: We can probably make this smaller with LVGL
#define SCREEN_BUF_SIZE (SCREEN_BYTES_PER_LINE * SCREEN_HEIGHT)

typedef struct {
    uint8_t header[2];
    union {
        uint8_t  pixels[SCREEN_BYTES_PER_LINE];
        uint16_t pixels_u16[SCREEN_BYTES_PER_LINE / 2];
    };
} ScreenLine;

typedef struct {
    ScreenLine lines[SCREEN_HEIGHT];
    uint16_t   dummy;
} Screen;

// Data structures for lcd_test pattern creation
typedef struct _LCDTestLine {
    uint8_t pixels[SCREEN_BYTES_PER_LINE];
} LCDTestLine;

typedef struct _LCDTestScreen {
    LCDTestLine lines[SCREEN_HEIGHT];
} LCDTestScreen;

// Colors
#define COLOR_BLACK 0
#define COLOR_WHITE 1

void     lcd_init(bool clear);
void     lcd_deinit(void);
void     lcd_fill(uint16_t color);
void     lcd_clear(uint16_t color);
void     lcd_update(bool invert);
void     lcd_update_rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* data);
void     lcd_update_viewfinder(uint8_t* grayscale, uint16_t gray_hor_res, uint16_t gray_ver_res);
void     lcd_draw_glyph(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* glyph, uint16_t color);
void     lcd_draw_image(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* image);
uint16_t lcd_get_glyph_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* image);
uint16_t lcd_get_image_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* image, uint16_t default_color);
void     lcd_set_pixel(int16_t x, int16_t y, uint16_t color);

#endif /* __LCD_SHARP_H__ */
