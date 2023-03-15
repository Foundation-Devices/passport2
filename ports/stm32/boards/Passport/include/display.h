// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// display.h - Display rendering functions for the Passport bootloader
#pragma once

#ifdef SCREEN_MODE_MONO
#include "lcd-sharp-ls018b7dh02.h"
#endif

#ifdef SCREEN_MODE_COLOR
#include "lcd-st7789.h"
#endif

#ifdef PASSPORT_BOOTLOADER
#include "lvgl.h"
#include "passport_fonts.h"
#endif

// Pass this constant to center text horizontally
#define CENTER_X 32767

// Bitmap draw mode bitmask
#define DRAW_MODE_NORMAL 0
#define DRAW_MODE_INVERT (1 << 0)
#define DRAW_MODE_WHITE_ONLY (1 << 1)
#define DRAW_MODE_BLACK_ONLY (1 << 2)
#define DRAW_MODE_INDEXED_1_BIT (1 << 3)
#define DRAW_MODE_INDEXED_2_BIT (1 << 4)
#define DRAW_MODE_INDEXED_4_BIT (1 << 5)
#define DRAW_MODE_INDEXED_8_BIT (1 << 6)
#define DRAW_MODE_RGB565 (1 << 7)

#define PROGRESS_BAR_MARGIN 22
#define PROGRESS_BAR_Y (SCREEN_HEIGHT - 22)
#define SPLASH_TEXT_BOTTOM_MARGIN 54

extern void display_init(bool clear);
extern void display_clear(uint16_t color);
extern void display_fill(uint16_t color);
extern void display_show(void);
extern void display_clean_shutdown(void);

#ifdef PASSPORT_BOOTLOADER
extern void     display_progress_bar(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t percent, char* message);
extern uint16_t display_measure_text(char* text, Font* font);
extern uint16_t display_get_char_width(char ch, Font* font);
extern void     display_text(char* text, int16_t x, int16_t y, Font* font, uint16_t color);
extern void     display_fill_rect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);
extern void     display_rect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color);
extern void     display_image(
        uint16_t x, uint16_t y, uint16_t image_w, uint16_t image_h, const uint8_t* image, uint8_t mode);
#endif
