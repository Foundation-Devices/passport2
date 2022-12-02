// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#ifndef __FRAMEBUFFER_H
#define __FRAMEBUFFER_H

#include <stdint.h>

#ifndef FACTORY_TEST
#include "../../../../lib/lv_bindings/driver/include/common.h"
#endif

#include "../../../../lib/lv_bindings/lv_conf.h"
#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

#if defined(SCREEN_MODE_MONO) && defined(SCREEN_MODE_COLOR)
#error "SCREEN_MODE_MONO and SCREEN_MODE_COLOR cannot be used at the same time"
#endif

// Camera framebuffer size.
#define CAMERA_HOR_RES (416U)
#define CAMERA_VER_RES (312U)
#define CAMERA_FRAMEBUFFER_PIXELS (CAMERA_HOR_RES * CAMERA_VER_RES)
#define CAMERA_FRAMEBUFFER_SIZE (CAMERA_FRAMEBUFFER_PIXELS * sizeof(uint16_t))

// Color screen framebuffer size.
#ifdef SCREEN_MODE_COLOR
// Color screen.
#define LCD_HOR_RES (240U)
#define LCD_VER_RES (320U)
#define LCD_LVGL_LINES (64U)
#define LCD_BIG_FRAMEBUFFER_PIXELS (LCD_HOR_RES * LCD_VER_RES)
#define LCD_BIG_FRAMEBUFFER_SIZE (LCD_BIG_FRAMEBUFFER_PIXELS * sizeof(lv_color_t))
#define LCD_SMALL_FRAMEBUFFER_PIXELS (LCD_HOR_RES * LCD_LVGL_LINES)
#define LCD_SMALL_FRAMEBUFFER_SIZE (LCD_SMALL_FRAMEBUFFER_PIXELS * sizeof(lv_color_t))
#endif  // SCREEN_MODE_COLOR

// Mono screen framebuffer size.
#ifdef SCREEN_MODE_MONO
#define LCD_HOR_RES (230U)
#define LCD_VER_RES (303U)
#define LCD_BUF_HOR_RES (240U)
#define LCD_FRAMEBUFFER_PIXELS (LCD_HOR_RES * LCD_VER_RES)
// Framebuffer size needs to be 240 pixels wide in order for the sharp screen
// to draw correctly.
#define LCD_FRAMEBUFFER_SIZE ((LCD_BUF_HOR_RES / 8) * LCD_VER_RES)
#endif  // SCREEN_MODE_MONO

void framebuffer_init();

uint16_t* framebuffer_camera(void);

void framebuffer_camera_lock(void);

void framebuffer_camera_unlock(void);

#endif  // __FRAMEBUFFER_H