// SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Unix build for the simulator.

#include <errno.h>
#include <stdio.h>

#include "py/obj.h"
#include "py/runtime.h"

#include "../../../../lib/lv_bindings/driver/include/common.h"
#include "../../../../lib/lv_bindings/lv_conf.h"
#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

#if defined(SCREEN_MODE_MONO) && defined(SCREEN_MODE_COLOR)
#error "SCREEN_MODE_MONO and SCREEN_MODE_COLOR cannot be used at the same time"
#endif

#ifndef LCD_DEBUG
#define LCD_DEBUG 0
#endif

#ifdef SCREEN_MODE_COLOR
#define LCD_HOR_RES (240U)
#define LCD_VER_RES (320U)
#define LCD_LVGL_BUF_PIXELS (LCD_HOR_RES * LCD_VER_RES)

static lv_color_t mod_passport_lv_lcd_buf1[LCD_LVGL_BUF_PIXELS];
#endif  // SCREEN_MODE_COLOR

#ifdef SCREEN_MODE_MONO
#define LCD_HOR_RES (230U)
#define LCD_VER_RES (303U)
// Sharp display needs a framebuffer of 240px in order to draw properly.
#define LCD_BUF_HOR_RES (240U)
#define LCD_LVGL_BUF_SIZE ((LCD_BUF_HOR_RES / 8) * LCD_VER_RES)
#define LCD_LVGL_BUF_PIXELS (LCD_HOR_RES * LCD_VER_RES)

static uint8_t mod_passport_lv_lcd_buf1[LCD_LVGL_BUF_SIZE];
#endif  // SCREEN_MODE_MONO

// Draw buffer and display driver are stored on normal RAM.
static lv_disp_draw_buf_t mod_passport_lv_lcd_draw_buf;
static lv_disp_drv_t      mod_passport_lv_lcd_disp_drv;
static int                mod_passport_lv_pipe_fd;

STATIC void mod_passport_lv_lcd_flush(lv_disp_drv_t* disp_drv, const lv_area_t* area, lv_color_t* color_p);
STATIC void mod_passport_lv_lcd_rounder(lv_disp_drv_t* disp_drv, lv_area_t* area);
STATIC void mod_passport_lv_lcd_set_px(lv_disp_drv_t* disp_drv,
                                       uint8_t*       buf,
                                       lv_coord_t     buf_w,
                                       lv_coord_t     x,
                                       lv_coord_t     y,
                                       lv_color_t     color,
                                       lv_opa_t       opa);

/// package: passport_lv.lcd

/// def init(self) -> None:
///     """
///     Initialize LVGL screen for the simulator. Parses argv[1] as the LCD
///     output file descriptor.
///     """
STATIC mp_obj_t mod_passport_lv_lcd_init(void) {
    mp_obj_list_t* mp_sys_argv_obj = &MP_STATE_VM(mp_sys_argv_obj);
    if (mp_sys_argv_obj->len < 2) {
        mp_raise_ValueError(MP_ERROR_TEXT("MicroPython arguments do not contain screen output file descriptor"));
    }
    mod_passport_lv_pipe_fd = atoi(mp_obj_str_get_str(mp_sys_argv_obj->items[1]));

    // Initialize LVGL if already not.
    if (!lv_is_initialized()) {
        lv_init();
    }

    // Initialize draw buffer configured to use double-buffering.
    lv_disp_draw_buf_t* draw_buf = &mod_passport_lv_lcd_draw_buf;
    lv_disp_draw_buf_init(draw_buf, &mod_passport_lv_lcd_buf1, NULL, LCD_LVGL_BUF_PIXELS);

    // Initialize display driver with the provided draw buffer.
    lv_disp_drv_t* disp_drv = &mod_passport_lv_lcd_disp_drv;
    lv_disp_drv_init(disp_drv);
    disp_drv->hor_res     = LCD_HOR_RES;
    disp_drv->ver_res     = LCD_VER_RES;
    disp_drv->draw_buf    = draw_buf;
    disp_drv->flush_cb    = mod_passport_lv_lcd_flush;
    disp_drv->rounder_cb  = mod_passport_lv_lcd_rounder;
    disp_drv->direct_mode = 1;
#ifdef SCREEN_MODE_MONO
    disp_drv->set_px_cb = mod_passport_lv_lcd_set_px;
#endif  // SCREEN_MODE_MONO
    lv_disp_drv_register(disp_drv);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_lv_lcd_init_obj, mod_passport_lv_lcd_init);

STATIC void mod_passport_lv_lcd_flush(lv_disp_drv_t* disp_drv, const lv_area_t* area, lv_color_t* color_p) {
#if defined(SCREEN_MODE_COLOR) || LCD_DEBUG
    lv_coord_t w = lv_area_get_width(area);
    lv_coord_t h = lv_area_get_height(area);
#endif

#if LCD_DEBUG
    printf("[passport_lv.lcd] Flush start\n");
    // mp_obj_LCD_t* lcd = m_new_obj(mp_obj_LCD_t);

    printf("[passport_lv.lcd] Flush: w=%" PRIu16 " h=%" PRIu16 " color_p=%p\n", w, h, color_p);

    // Send over pipe - for simulator we always send the whole screen
    printf("[passport_lv.lcd] write start.\n");
    uint16_t* buf = (uint16_t*)color_p;
    for (uint16_t y = 0; y < h; y++) {
        printf("==================================================\ny=%d\n", y);
        for (uint16_t x = 0; x < w; x++) {
            size_t tmp = ((size_t)y * (size_t)w) + (size_t)x;
            printf("%04x ", (unsigned)buf[tmp]);
        }
        printf("\n");
    }
#endif  // LCD_DEBUG

#ifdef SCREEN_MODE_COLOR
    size_t size = (size_t)w * (size_t)h * sizeof(lv_color_t);
    int    ret  = write(mod_passport_lv_pipe_fd, color_p, size);
#endif  // SCREEN_MODE_COLOR

#ifdef SCREEN_MODE_MONO
    // Write entire buffer even if we are on direct mode as LVGL thinks we have
    // less pixels in the framebuffer.
    int ret = write(mod_passport_lv_pipe_fd, mod_passport_lv_lcd_buf1, sizeof(mod_passport_lv_lcd_buf1));
#endif  // SCREEN_MODE_MONO

    if (ret == -1) {
        printf("[passport_lv.lcd] failed.\n");
    } else {
        lv_disp_flush_ready(disp_drv);
    }

#if LCD_DEBUG
    printf("[passport_lv.lcd] Flush done.\n");
#endif  // LCD_DEBUG
}

// NOTE: only used by the "mono" simulator.
STATIC void mod_passport_lv_lcd_rounder(lv_disp_drv_t* disp_drv, lv_area_t* area) {
#if LCD_DEBUG
    printf("[passport_lv.lcd] rounder: x1=%u x2=%u y1=%u y2=%u\n", (unsigned)area->x1, (unsigned)area->x2,
           (unsigned)area->y1, (unsigned)area->y2);
#endif  // LCD_DEBUG

#ifdef SCREEN_MODE_COLOR
    area->x1 = 0;
    area->x2 = 239;
    area->y1 = 0;
    area->y2 = 319;
#endif

#ifdef SCREEN_MODE_MONO
    area->x1 = 0;
    area->x2 = 229;
    area->y1 = 0;
    area->y2 = 302;
#endif

#if LCD_DEBUG
    printf("[passport_lv.lcd] new rounder values: x1=%u x2=%u y1=%u y2=%u\n", (unsigned)area->x1, (unsigned)area->x2,
           (unsigned)area->y1, (unsigned)area->y2);
#endif  // LCD_DEBUG
}

// NOTE: only used by the "mono" simulator.
STATIC void mod_passport_lv_lcd_set_px(lv_disp_drv_t* disp_drv,
                                       uint8_t*       buf,
                                       lv_coord_t     buf_w,
                                       lv_coord_t     x,
                                       lv_coord_t     y,
                                       lv_color_t     color,
                                       lv_opa_t       opa) {
#if LCD_DEBUG
    printf("[passport_lv.lcd] set_px: buf_w=%u x=%u y=%u\n", (unsigned)buf_w, (unsigned)x, (unsigned)y);
#endif  // LCD_DEBUG

    buf += 30 * y;
    buf += x >> 3;
    if (lv_color_brightness(color) > 128) {
        (*buf) |= (1 << (7 - (x & 0x07)));
    } else {
        (*buf) &= ~(1 << (7 - (x & 0x07)));
    }
}

STATIC const mp_rom_map_elem_t mod_passport_lv_lcd_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_lcd)},
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_passport_lv_lcd_init_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_lv_lcd_globals, mod_passport_lv_lcd_globals_table);

STATIC const mp_obj_module_t mod_passport_lv_lcd_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_passport_lv_lcd_globals,
};
