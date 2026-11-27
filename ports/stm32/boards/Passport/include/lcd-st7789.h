// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Driver for ST7789 display with 240x320 RGB565 display

#ifndef __LCD_ST7789_H__
#define __LCD_ST7789_H__

#include "stm32h7xx_hal.h"
#include "st7789.h"

#include <stdbool.h>

#define SCREEN_WIDTH 240
#define SCREEN_HEIGHT 320
#define SCREEN_BUFFER_WIDTH 240
#define SCREEN_BITS_PER_PIXEL 16
#define NUM_LVGL_BUF_LINES 32

#define SCREEN_BYTES_PER_LINE (SCREEN_BUFFER_WIDTH / 8)

#define SCREEN_BUF_SIZE (SCREEN_BYTES_PER_LINE * NUM_LVGL_BUF_LINES)

// Colors
#define COLOR_BLACK 0x0000
#define COLOR_WHITE 0xFFFF
#define COLOR_ORANGE 0xFA60
#define COLOR_FD_BLUE 0x05F9
#define COLOR_FD_COPPER 0xBC0E
#define COLOR_TEXT_GREY 0x632C

void lcd_init(bool clear);
void lcd_deinit(void);
void lcd_update_rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* data);
void lcd_clear(uint16_t color);
void lcd_fill(uint16_t color);

#ifdef PASSPORT_BOOTLOADER

void     lcd_update(bool invert);
void     lcd_draw_glyph(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* glyph, uint16_t color);
void     lcd_draw_image_indexed(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint8_t* image, uint8_t bits);
void     lcd_draw_image_rgb565(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint8_t* image);
uint16_t lcd_get_glyph_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* image);
uint32_t lcd_get_image_pixel(int16_t        x,
                             int16_t        y,
                             uint16_t       w,
                             uint16_t       h,
                             const uint8_t* image,
                             uint16_t       default_color,
                             uint8_t        bits,
                             uint8_t*       alpha);
void     lcd_set_pixel(int16_t x, int16_t y, uint16_t color);
uint16_t lcd_get_pixel(int16_t x, int16_t y);

#endif

#endif /* __LCD_ST7789_H__ */
