// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Driver for ST7789 display with 240x320 RGB565 display

#include <string.h>

#include "lcd-st7789.h"

void lcd_init(bool clear) {
    ST7789_Init(clear);
}

void lcd_deinit(void) {}

void lcd_update_rect(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* data) {
    ST7789_Update_Rect(x, y, w, h, data);
}

void lcd_clear(uint16_t color) {
    ST7789_Clear(color);
}

#ifdef PASSPORT_BOOTLOADER
// Would prfer that the bootloader code and firmware not share this file since they work with the hardware differently.
// This screen buffer should NEVER be used by the firmware!
// Use AXI SRAM as a fullscreen display buffer
uint16_t* screen = (uint16_t*)0x24000000;

void lcd_update(bool invert) {
    // Write the screen data to the screen all at once.
    // This is much faster than separate writes for each line.
    ST7789_Update_Rect(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT, (uint8_t*)screen);
}

void lcd_fill(uint16_t color) {
    for (uint32_t i = 0; i < SCREEN_WIDTH * SCREEN_HEIGHT; i++) {
        screen[i] = color;
    }
}

void lcd_draw_glyph(uint16_t x, uint16_t y, uint16_t w, uint16_t h, uint8_t* glyph, uint16_t color) {
    // Since the image is palettized, we need to draw it pixel-by-pixel :( Sad!
    for (uint32_t cy = 0; cy < h; cy++) {
        for (uint32_t cx = 0; cx < w; cx++) {
            uint16_t glyph_color = lcd_get_glyph_pixel(cx, cy, w, h, glyph);
            if (glyph_color == COLOR_BLACK) {
                lcd_set_pixel(x + cx, y + cy, color);
            }
        }
    }
}

uint16_t alpha_blend_rgb565(uint32_t fg, uint32_t bg, uint8_t alpha) {
    alpha           = (alpha + 4) >> 3;
    bg              = (bg | (bg << 16)) & 0x7E0F81F;
    fg              = (fg | (fg << 16)) & 0x7E0F81F;
    uint32_t result = ((((fg - bg) * alpha) >> 5) + bg) & 0x7E0F81F;
    return (uint16_t)((result >> 16) | result);
}

void lcd_draw_image_indexed(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint8_t* image, uint8_t bits) {
    for (uint32_t cy = 0; cy < h; cy++) {
        for (uint32_t cx = 0; cx < w; cx++) {
            /*
            uint8_t bit = cx & 0x7;
            uint8_t tmp_x = cx >> 3;
            uint32_t px  = ((w + 7) >> 3) * cy + tmp_x;
            uint32_t index = ((image_data[px] & (1 << (7 - bit))) >> (7 - bit));
            index *= 4;

            uint8_t img_a = palette[index + 3];
            uint32_t img_r = (((uint32_t)palette[index + 2] >> 3) & 0x1F) << 11;
            uint32_t img_g = (((uint32_t)palette[index + 1] >> 2) & 0x3F) << 5;
            uint32_t img_b = (((uint32_t)palette[index + 0] >> 3) & 0x1F);
            */
            uint8_t  alpha;
            uint32_t fg = lcd_get_image_pixel(cx, cy, w, h, image, 0x0000, bits, &alpha);
            uint32_t bg = lcd_get_pixel(x + cx, y + cy);

            uint16_t color = alpha_blend_rgb565(fg, bg, alpha);
            lcd_set_pixel(x + cx, y + cy, color);
        }
    }
}

void lcd_draw_image_rgb565(uint16_t x, uint16_t y, uint16_t w, uint16_t h, const uint8_t* image) {
    for (uint32_t cy = 0; cy < h; cy++) {
        for (uint32_t cx = 0; cx < w; cx++) {
            lcd_set_pixel(x + cx, y + cy, ((uint16_t*)image)[(cy * w) + cx]);
        }
    }
}

uint16_t lcd_get_glyph_pixel(int16_t x, int16_t y, uint16_t w, uint16_t h, uint8_t* glyph) {
    if (x < 0 || x >= w || y < 0 || y >= h) {
        return COLOR_BLACK;
    }

    uint16_t w_bytes = (w + 7) / 8;
    uint16_t offset  = (y * w_bytes) + x / 8;
    uint8_t  bit     = 1 << (7 - x % 8);

    return ((glyph[offset] & bit) == 0) ? COLOR_WHITE : COLOR_BLACK;
}

uint32_t lcd_get_image_pixel(int16_t        x,
                             int16_t        y,
                             uint16_t       w,
                             uint16_t       h,
                             const uint8_t* image,
                             uint16_t       default_color,
                             uint8_t        bits,
                             uint8_t*       alpha) {
    const uint8_t* palette    = image;
    const uint8_t* image_data = image;
    uint32_t       index;

    if (x < 0 || x >= w || y < 0 || y >= h) {
        return default_color;
    }

    if (bits == 1) {
        image_data += 2 * 4 * sizeof(uint8_t);
        uint8_t  bit   = x & 0x7;
        uint8_t  tmp_x = x >> 3;
        uint32_t px    = ((w + 7) >> 3) * y + tmp_x;
        index          = ((image_data[px] & (1 << (7 - bit))) >> (7 - bit));
        image_data += (2 * 4 * sizeof(uint8_t));
    } else if (bits == 2) {
        image_data += 4 * 4 * sizeof(uint8_t);
        uint8_t  bit   = (x & 0x3) * 2;
        uint8_t  tmp_x = x >> 2;
        uint32_t px    = ((w + 1) >> 2) * y + tmp_x;
        index          = (image_data[px] & (0x3 << (6 - bit))) >> (6 - bit);
    } else if (bits == 4) {
        image_data += 16 * 4 * sizeof(uint8_t);
        uint8_t  bit   = (x & 0x1) * 4;
        uint8_t  tmp_x = x >> 1;
        uint32_t px    = ((w + 1) >> 1) * y + tmp_x;
        index          = (image_data[px] & (0xF << (4 - bit))) >> (4 - bit);
    } else if (bits == 8) {
        image_data += 256 * 4 * sizeof(uint8_t);
        uint32_t px = (y * w) + x;
        index       = image_data[px];
    } else {
        return default_color;
    }

    index *= 4;

    *alpha         = palette[index + 3];
    uint32_t img_r = (((uint32_t)palette[index + 2] >> 3) & 0x1F) << 11;
    uint32_t img_g = (((uint32_t)palette[index + 1] >> 2) & 0x3F) << 5;
    uint32_t img_b = (((uint32_t)palette[index + 0] >> 3) & 0x1F);

    return img_r | img_g | img_b;
}

void lcd_set_pixel(int16_t x, int16_t y, uint16_t color) {
    if (x < 0 || x >= SCREEN_WIDTH || y < 0 || y >= SCREEN_HEIGHT) {
        return;
    }

    uint32_t offset = (y * SCREEN_WIDTH) + x;
    screen[offset]  = (color >> 8) | ((color & 0xFF) << 8);
}

uint16_t lcd_get_pixel(int16_t x, int16_t y) {
    if (x < 0 || x >= SCREEN_WIDTH || y < 0 || y >= SCREEN_HEIGHT) {
        return 0;
    }

    uint16_t pixel = screen[((size_t)y * SCREEN_WIDTH) + (size_t)x];
    return (pixel >> 8) | (pixel << 8);
}
#endif
