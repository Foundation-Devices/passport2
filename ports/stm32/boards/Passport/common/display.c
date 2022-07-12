// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// display.c - Display rendering functions for the Passport bootloader

#include <string.h>

#include "display.h"
#include "gpio.h"
#include "keypad-adp-5587.h"
#include "utils.h"

#ifdef PASSPORT_BOOTLOADER
#include "lvgl.h"
#include "images.h"
#endif

void display_init(bool clear) {
    lcd_init(clear);
}

void display_fill(uint16_t color) {
    lcd_fill(color);
}

void display_clear(uint16_t color) {
    lcd_clear(color);
}

void display_show(void) {
    __disable_irq();

#ifdef SCREEN_MODE_COLOR
#ifdef PASSPORT_BOOTLOADER
    lcd_update(false);
#endif
    // This is a no-op on the main firmware in color devices
#endif

#ifdef SCREEN_MODE_MONO
    // Disable IRQs so keypad events don't interrupt display drawing
    lcd_update(true);
#endif

    __enable_irq();

#ifndef DEBUG
    // Clear the keypad interrupt so that it will retrigger if it had any events while
    // interrupts were disabled, else it will hang the controller since it's waiting
    // for the previous interrupt to be acknowledged.
    keypad_write(KBD_ADDR, KBD_REG_INT_STAT, 0xFF);
#endif /* DEBUG */
}

// Clear the memory display and then shutdown
void display_clean_shutdown() {
    display_clear(COLOR_BLACK);
    display_show();
    passport_shutdown();
    while (true)
        ;
}

#ifdef PASSPORT_BOOTLOADER
uint16_t display_measure_text(char* text, Font* font) {
    uint16_t width = 0;
    uint16_t slen  = strlen(text);
    for (int i = 0; i < slen; i++) {
        GlyphInfo glyphInfo;
        glyph_lookup(font, text[i], &glyphInfo);
        width += glyphInfo.advance;
    }
    return width;
}

void display_fill_rect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) {
    for (int dy = y; dy < y + h; dy++) {
        for (int dx = x; dx < x + w; dx++) {
            lcd_set_pixel(dx, dy, color);
        }
    }
}

void display_text(char* text, int16_t x, int16_t y, Font* font, uint16_t color) {
    if (x == CENTER_X) {
        uint16_t text_width = display_measure_text(text, font);
        x                   = SCREEN_WIDTH / 2 - text_width / 2;
    }

    uint16_t slen = strlen(text);
    for (int i = 0; i < slen; i++) {
        GlyphInfo glyphInfo;
        glyph_lookup(font, text[i], &glyphInfo);

        // y + font.ascent - fn.h - fn.y
        display_glyph(x + glyphInfo.x, y + font->ascent - glyphInfo.h - glyphInfo.y, glyphInfo.w, glyphInfo.h,
                      glyphInfo.bitmap, color);
        x += glyphInfo.advance;
    }
}

uint16_t display_get_char_width(char ch, Font* font) {
    GlyphInfo glyphInfo;
    glyph_lookup(font, ch, &glyphInfo);
    return glyphInfo.advance;
}

void display_rect(int16_t x, int16_t y, int16_t w, int16_t h, uint16_t color) {
    // Draw the top and bottom
    int16_t y_bottom = y + h - 1;
    for (int dx = x; dx < x + w; dx++) {
        lcd_set_pixel(dx, y, color);
        lcd_set_pixel(dx, y_bottom, color);
    }

    // Draw the sides - repeats the top and bottom pixels to avoid special case
    // code for short rectangles
    int16_t x_right = x + w - 1;
    for (int dy = y; dy < y + w; dy++) {
        lcd_set_pixel(x, dy, color);
        lcd_set_pixel(x_right, dy, color);
    }
}

// Very simple and inefficient image drawing, but should be fast enough for our
// limited use.
void display_image(uint16_t x, uint16_t y, uint16_t image_w, uint16_t image_h, const uint8_t* image, uint8_t mode) {
#ifdef SCREEN_MODE_COLOR
    if (mode == DRAW_MODE_INDEXED_1_BIT) {
        lcd_draw_image_indexed(x, y, image_w, image_h, image, 1);
    } else if (mode == DRAW_MODE_INDEXED_2_BIT) {
        lcd_draw_image_indexed(x, y, image_w, image_h, image, 2);
    } else if (mode == DRAW_MODE_INDEXED_4_BIT) {
        lcd_draw_image_indexed(x, y, image_w, image_h, image, 4);
    } else if (mode == DRAW_MODE_INDEXED_8_BIT) {
        lcd_draw_image_indexed(x, y, image_w, image_h, image, 8);
    } else if (mode == DRAW_MODE_RGB565) {
        lcd_draw_image_rgb565(x, y, image_w, image_h, image);
    }
#endif
}

void display_repeat_image_horiz(
    uint16_t x, uint16_t y, const lv_img_dsc_t* image, uint16_t repeat_count, uint8_t mode) {
    uint16_t curr_x = x;
    for (uint16_t i = 0; i < repeat_count; i++) {
        display_image(curr_x, y, image->header.w, image->header.h, image->data, mode);
        curr_x += image->header.w;
    }
}

void display_glyph(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* glyph, uint16_t color) {
    lcd_draw_glyph(x, y, w, h, glyph, color);
}

// Assumes it's the only thing on these lines, so it does not retain any other
// image that might have been rendered there.
void display_progress_bar(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t percent, char* message) {
#ifndef DEBUG
    display_image(0, 0, SPLASH.header.w, SPLASH.header.h, SPLASH.data, lv_cf_mode_to_draw_mode(SPLASH.header.cf));
#endif
    x = x + PROGRESS_CAP_LEFT.header.w;
    w = w - PROGRESS_CAP_LEFT.header.w - PROGRESS_CAP_RIGHT.header.w;

    uint16_t fill_width = (percent * w) / 100;

    // We don't bother to draw a left end cap, as we would always immediately overwrite it below

    // Draw background track image all the way across
    display_repeat_image_horiz(x, y, &PROGRESS_BAR_BG, w, lv_cf_mode_to_draw_mode(PROGRESS_BAR_BG.header.cf));

    // Right end cap background
    display_image(x + w, y, PROGRESS_CAP_RIGHT_BG.header.w, PROGRESS_CAP_RIGHT_BG.header.h, PROGRESS_CAP_RIGHT_BG.data,
                  lv_cf_mode_to_draw_mode(PROGRESS_CAP_RIGHT_BG.header.cf));

    // Left end cap
    display_image(x - PROGRESS_CAP_LEFT.header.w, y, PROGRESS_CAP_LEFT.header.w, PROGRESS_CAP_LEFT.header.h,
                  PROGRESS_CAP_LEFT.data, lv_cf_mode_to_draw_mode(PROGRESS_CAP_LEFT.header.cf));

    display_repeat_image_horiz(x, y, &PROGRESS_BAR_FG, fill_width, lv_cf_mode_to_draw_mode(PROGRESS_BAR_FG.header.cf));

    // Right end cap
    display_image(x + fill_width, y, PROGRESS_CAP_RIGHT.header.w, PROGRESS_CAP_RIGHT.header.h, PROGRESS_CAP_RIGHT.data,
                  lv_cf_mode_to_draw_mode(PROGRESS_BAR_FG.header.cf));

    display_text(message, CENTER_X, SCREEN_HEIGHT - SPLASH_TEXT_BOTTOM_MARGIN, &FontTiny, COLOR_TEXT_GREY);

    display_show();
}

#endif
