// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"

#include "backlight.h"

/// package: passport

/// class Backlight:
///     """
///     """
typedef struct _mp_obj_Backlight_t {
    mp_obj_base_t base;
} mp_obj_Backlight_t;

/// def __init__(self):
///     """
///     """
STATIC mp_obj_t mod_passport_Backlight_make_new(const mp_obj_type_t* type,
                                                size_t n_args,
                                                size_t n_kw,
                                                const mp_obj_t* args) {
    mp_obj_Backlight_t* backlight = m_new_obj(mp_obj_Backlight_t);
    backlight->base.type          = type;
    backlight_minimal_init();
    return MP_OBJ_FROM_PTR(backlight);
}

/// def intensity(self, intensity: int) -> None:
///     """
///     Set backlight intensity
///     """
STATIC mp_obj_t mod_passport_Backlight_intensity(mp_obj_t self_in, mp_obj_t intensity_obj) {
    uint16_t intensity = mp_obj_get_int(intensity_obj);
    backlight_intensity(intensity);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_Backlight_intensity_obj, mod_passport_Backlight_intensity);

STATIC const mp_rom_map_elem_t mod_passport_Backlight_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_intensity),    MP_ROM_PTR(&mod_passport_Backlight_intensity_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_Backlight_locals_dict, mod_passport_Backlight_locals_dict_table);

const mp_obj_type_t mod_passport_Backlight_type = {
    {&mp_type_type},
    .name           = MP_QSTR_Backlight,
    .make_new       = mod_passport_Backlight_make_new,
    .locals_dict    = (mp_obj_dict_t*)&mod_passport_Backlight_locals_dict,
};