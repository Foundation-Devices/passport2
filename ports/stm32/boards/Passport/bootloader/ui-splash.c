// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc.
// <hello@foundationdevices.com> SPDX-License-Identifier: GPL-3.0-or-later
//
// Splash screen shown at during initialization

#include "display.h"
#include "ui.h"

#ifdef SCREEN_MODE_COLOR
#include "lvgl.h"
#include "images.h"
#endif

#ifdef SCREEN_MODE_MONO
#include "bootloader_graphics.h"
#define SPLASH_WIDTH (splash_img.width)
#define SPLASH_HEIGHT (splash_img.height)
#define SPLASH_DATA (splash_img.data)
#endif

void show_splash(char* message) {
#ifdef SCREEN_MODE_COLOR
#ifdef COLORWAY_LIGHT
    display_image(0, 0, SPLASH_LIGHT.header.w, SPLASH_LIGHT.header.h, SPLASH_LIGHT.data, DRAW_MODE_INDEXED_8_BIT);
#else
    display_image(0, 0, SPLASH_DARK.header.w, SPLASH_DARK.header.h, SPLASH_DARK.data, DRAW_MODE_INDEXED_8_BIT);
#endif
#else
    display_fill(COLOR_WHITE);
#endif
    display_text(message, CENTER_X, SCREEN_HEIGHT - SPLASH_TEXT_BOTTOM_MARGIN, &FontTiny, COLOR_TEXT_GREY);
    display_show();
}
