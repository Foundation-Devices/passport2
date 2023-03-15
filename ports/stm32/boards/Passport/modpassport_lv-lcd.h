// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"

#include "framebuffer.h"

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

#ifdef SCREEN_MODE_MONO
STATIC mp_obj_t mod_passport_lv_lcd_update_viewfinder_direct(size_t n_args, const mp_obj_t* args) {
    mp_buffer_info_t grayscale_info;
    mp_get_buffer_raise(args[0], &grayscale_info, MP_BUFFER_READ);

    mp_int_t hor_res = mp_obj_get_int(args[1]);
    mp_int_t ver_res = mp_obj_get_int(args[2]);

    lcd_update_viewfinder(grayscale_info.buf, hor_res, ver_res);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_passport_lv_lcd_update_viewfinder_direct_obj,
                                           3,
                                           3,
                                           mod_passport_lv_lcd_update_viewfinder_direct);
#endif

STATIC const mp_rom_map_elem_t mod_passport_lv_lcd_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_init), MP_ROM_PTR(&mod_passport_lv_lcd_init_obj)},
#ifdef SCREEN_MODE_MONO
    {MP_ROM_QSTR(MP_QSTR_update_viewfinder_direct), MP_ROM_PTR(&mod_passport_lv_lcd_update_viewfinder_direct_obj)},
#endif
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_lv_lcd_globals, mod_passport_lv_lcd_globals_table);

STATIC const mp_obj_module_t mod_passport_lv_lcd_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_passport_lv_lcd_globals,
};