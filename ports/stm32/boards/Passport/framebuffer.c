// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//

#include <stdbool.h>
#include <string.h>

#include "py/obj.h"
#include "py/mphal.h"
#include "irq.h"
#include "pins.h"

#include "keypad-adp-5587.h"

#ifdef SCREEN_MODE_MONO
#include "keypad-adp-5587.h"
#include "lcd-sharp-ls018b7dh02.h"
#endif

#ifdef SCREEN_MODE_COLOR
#include "lcd-st7789.h"
#endif

#include "framebuffer.h"

static void _lcd_flush(lv_disp_drv_t* disp_drv, const lv_area_t* area, lv_color_t* color_p);
#ifdef SCREEN_MODE_MONO
static void _lcd_rounder(lv_disp_drv_t* disp_drv, lv_area_t* area);
static void _lcd_set_px(lv_disp_drv_t* disp_drv,
                        uint8_t*       buf,
                        lv_coord_t     buf_w,
                        lv_coord_t     x,
                        lv_coord_t     y,
                        lv_color_t     color,
                        lv_opa_t       opa);
#endif  // SCREEN_MODE_MONO

#ifdef SCREEN_MODE_COLOR
#define _FRAMEBUF_MAX(a, b) ((a) > (b) ? (a) : (b))
#define FRAMEBUFFER_SIZE (_FRAMEBUF_MAX(CAMERA_FRAMEBUFFER_SIZE, LCD_BIG_FRAMEBUFFER_SIZE) + LCD_SMALL_FRAMEBUFFER_SIZE)

static __attribute__((section(".dma_buffers"))) uint8_t _shared_framebuffer[FRAMEBUFFER_SIZE];

static bool _camera_in_use;

static lv_disp_drv_t      _big_lcd_disp_drv;
static lv_disp_draw_buf_t _big_lcd_draw_buf;

static lv_disp_drv_t      _small_lcd_disp_drv;
static lv_disp_draw_buf_t _small_lcd_draw_buf;

static lv_disp_t* _lcd_disp;
#endif  // SCREEN_MODE_COLOR

#ifdef SCREEN_MODE_MONO
static __attribute__((section(".dma_buffers"))) uint8_t _camera_framebuffer[CAMERA_FRAMEBUFFER_SIZE];
static __attribute__((section(".dma_buffers"))) uint8_t _lcd_framebuffer[LCD_FRAMEBUFFER_SIZE];
static lv_disp_drv_t                                    _lcd_disp_drv;
static lv_disp_draw_buf_t                               _lcd_draw_buf;
#endif  // SCREEN_MODE_MONO

void framebuffer_init() {
    lv_disp_drv_t*      disp_drv = NULL;
    lv_disp_draw_buf_t* draw_buf = NULL;

    // Initialize LVGL if already not.
    if (!lv_is_initialized()) {
        lv_init();
    }

    mp_hal_pin_config(MICROPY_HW_LCD_TE_PIN, MP_HAL_PIN_MODE_INPUT, MP_HAL_PIN_PULL_NONE, 0);

#ifdef SCREEN_MODE_COLOR
    _camera_in_use = false;

    draw_buf = &_big_lcd_draw_buf;
    disp_drv = &_big_lcd_disp_drv;

    lv_disp_draw_buf_init(&_big_lcd_draw_buf, &_shared_framebuffer, NULL, LCD_BIG_FRAMEBUFFER_PIXELS);
    lv_disp_draw_buf_init(&_small_lcd_draw_buf, &_shared_framebuffer[CAMERA_FRAMEBUFFER_SIZE], NULL,
                          LCD_SMALL_FRAMEBUFFER_PIXELS);
#endif  // SCREEN_MODE_COLOR

#ifdef SCREEN_MODE_MONO
    draw_buf = &_lcd_draw_buf;
    disp_drv = &_lcd_disp_drv;

    lv_disp_draw_buf_init(draw_buf, &_lcd_framebuffer, NULL, LCD_FRAMEBUFFER_PIXELS);
#endif  // SCREEN_MODE_MONO

    lv_disp_drv_init(disp_drv);
    disp_drv->hor_res  = LCD_HOR_RES;
    disp_drv->ver_res  = LCD_VER_RES;
    disp_drv->draw_buf = draw_buf;
    disp_drv->flush_cb = _lcd_flush;
#ifdef SCREEN_MODE_COLOR
    memcpy(&_small_lcd_disp_drv, &_big_lcd_disp_drv, sizeof(lv_disp_drv_t));
    _small_lcd_disp_drv.draw_buf    = &_small_lcd_draw_buf;
    _small_lcd_disp_drv.direct_mode = 0;
    _lcd_disp                       = lv_disp_drv_register(disp_drv);
#endif  // SCREEN_MODE_COLOR
#ifdef SCREEN_MODE_MONO
    disp_drv->rounder_cb = _lcd_rounder;
    disp_drv->set_px_cb  = _lcd_set_px;
    lv_disp_drv_register(disp_drv);
#endif  // SCREEN_MODE_MONO

    mp_hal_pin_config(MICROPY_HW_LCD_TE_PIN, MP_HAL_PIN_MODE_INPUT, MP_HAL_PIN_PULL_NONE, 0);
}

uint16_t* framebuffer_camera(void) {
#ifdef SCREEN_MODE_COLOR
    if (_camera_in_use) {
        return (uint16_t*)_shared_framebuffer;
    }

    return NULL;
#endif  // SCREEN_MODE_COLOR
#ifdef SCREEN_MODE_MONO
    return (uint16_t*)_camera_framebuffer;
#endif  // SCREEN_MODE_MONO
}

void framebuffer_camera_lock(void) {
#ifdef SCREEN_MODE_COLOR
    if (!_camera_in_use) {
        // Switch the display driver to use a the small framebuffer.
        lv_disp_drv_update(_lcd_disp, &_small_lcd_disp_drv);
        _camera_in_use = true;
    }

#endif  // SCREEN_MODE_COLOR
}

void framebuffer_camera_unlock(void) {
#ifdef SCREEN_MODE_COLOR
    if (_camera_in_use) {
        // Switch the display driver to use all of the framebuffer.
        lv_disp_drv_update(_lcd_disp, &_big_lcd_disp_drv);
        _camera_in_use = false;
    }
#endif  // SCREEN_MODE_COLOR
}

static void _lcd_flush(lv_disp_drv_t* disp_drv, const lv_area_t* area, lv_color_t* color_p) {
    uint16_t w = lv_area_get_width(area);
    uint16_t h = lv_area_get_height(area);

#ifdef SCREEN_MODE_MONO
    mp_uint_t state = PASSPORT_KEYPAD_BEGIN_ATOMIC_SECTION();
    lcd_update_rect(area->x1, area->y1, w, h, (uint8_t*)color_p);
    PASSPORT_KEYPAD_END_ATOMIC_SECTION(state);
#endif  // SCREEN_MODE_MONO
#ifdef SCREEN_MODE_COLOR
    // DISABLE BECAUSE THIS CAUSES A LOCKUP ON THE TEST FIXTURE, WHICH DOESN'T CONNECT THE TE PIN
    // while (mp_hal_pin_read(MICROPY_HW_LCD_TE_PIN)) {}
    lcd_update_rect(area->x1, area->y1, w, h, (uint8_t*)color_p);
#endif  // SCREEN_MODE_COLOR
    lv_disp_flush_ready(disp_drv);
}

#ifdef SCREEN_MODE_MONO

static void _lcd_rounder(lv_disp_drv_t* disp_drv, lv_area_t* area) {
    // The Sharp display only allows writing whole lines, so expand the rectangle to cover the
    // full width of the screen.
    area->x1 = 0;
    area->x2 = LCD_HOR_RES - 1;

    // LVGL sometimes miscalculates the update region by 1 pixel on the bottom, so we expand the region
    // It's possible we might expand it more than once when coalescing multiple regions, but this is not
    // going to affect performance in a noticeable way.
    area->y2 = MIN(area->y2 + 1, LCD_VER_RES - 1);
}

uint8_t byte_lookup_table[] = {
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1, 128, 64, 32, 16, 8, 4, 2, 1,
    128, 64, 32, 16, 8, 4};

static void _lcd_set_px(lv_disp_drv_t* disp_drv,
                        uint8_t*       buf,
                        lv_coord_t     buf_w,
                        lv_coord_t     x,
                        lv_coord_t     y,
                        lv_color_t     color,
                        lv_opa_t       opa) {
    buf += 30 * y;
    buf += x >> 3;
    uint8_t byte_value = byte_lookup_table[x];

    if (lv_color_brightness(color) > 96) {
        (*buf) |= byte_value;
    } else {
        (*buf) &= ~byte_value;
    }
}
#endif  // SCREEN_MODE_MONO
