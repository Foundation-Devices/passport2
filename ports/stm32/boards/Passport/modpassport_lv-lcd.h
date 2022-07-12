// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"

#include "framebuffer.h"

#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

/// package: passport_lv.lcd

/// def init() -> None:
///     """
///     Initialize LVGL screen.
///     """
STATIC mp_obj_t mod_passport_lv_lcd_init(void) {
    framebuffer_init();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_lv_lcd_init_obj, mod_passport_lv_lcd_init);

STATIC const mp_rom_map_elem_t mod_passport_lv_lcd_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_passport_lv_lcd_init_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_lv_lcd_globals, mod_passport_lv_lcd_globals_table);

STATIC const mp_obj_module_t mod_passport_lv_lcd_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_passport_lv_lcd_globals,
};