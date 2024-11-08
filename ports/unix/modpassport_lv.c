// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Unix build for the simulator.

#include "py/obj.h"

#include "modpassport_lv-keypad.h"
#include "modpassport_lv-lcd.h"

/// package: passport_lv

/// def __del__(self):
///     """
///     """
STATIC mp_obj_t mod_passport_lv___del__(mp_obj_t self) {
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_lv__del___obj, mod_passport_lv___del__);

/* Module Global configuration */
/* Define all properties of the module.
 * Table entries are key/value pairs of the attribute name (a string)
 * and the MicroPython object reference.
 * All identifiers and strings are written as MP_QSTR_xxx and will be
 * optimized to word-sized integers by the build system (interned strings).
 */
STATIC const mp_rom_map_elem_t passport_lv_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_passport_lv)},
    {MP_ROM_QSTR(MP_QSTR___del__), MP_ROM_PTR(&mod_passport_lv__del___obj)},
    {MP_ROM_QSTR(MP_QSTR_lcd), MP_ROM_PTR(&mod_passport_lv_lcd_module)},
    {MP_ROM_QSTR(MP_QSTR_Keypad), MP_ROM_PTR(&mod_passport_lv_Keypad_type)},
};
STATIC MP_DEFINE_CONST_DICT(passport_lv_module_globals, passport_lv_module_globals_table);

const mp_obj_module_t passport_lv_user_cmodule = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&passport_lv_module_globals,
};
MP_REGISTER_MODULE(MP_QSTR_passport_lv, passport_lv_user_cmodule, PASSPORT_FOUNDATION_ENABLED);