// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Passport hardware build only. It is not shared
// with the unix simulator.

#include "py/obj.h"

// For lcd_deinit
#ifdef SCREEN_MODE_MONO
#include "lcd-sharp-ls018b7dh02.h"
#endif
#ifdef SCREEN_MODE_COLOR
#include "lcd-st7789.h"
#endif

#include "modpassport_lv-lcd.h"
#include "modpassport_lv-keypad.h"

/// package: passport_lv

/* Module Global configuration */
/* Define all properties of the module.
 * Table entries are key/value pairs of the attribute name (a string)
 * and the MicroPython object reference.
 * All identifiers and strings are written as MP_QSTR_xxx and will be
 * optimized to word-sized integers by the build system (interned strings).
 * NOTE: Keep modules in alphabetical order.
 */
STATIC const mp_rom_map_elem_t passport_lv_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_passport_lv)},
    {MP_ROM_QSTR(MP_QSTR_lcd), MP_ROM_PTR(&mod_passport_lv_lcd_module)},
    {MP_ROM_QSTR(MP_QSTR_Keypad), MP_ROM_PTR(&mod_passport_lv_Keypad_type)},
};
STATIC MP_DEFINE_CONST_DICT(passport_lv_module_globals, passport_lv_module_globals_table);

/* Define module object. */
const mp_obj_module_t passport_lv_user_cmodule = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&passport_lv_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_passport_lv, passport_lv_user_cmodule, PASSPORT_FOUNDATION_ENABLED);
