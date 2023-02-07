// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "py/runtime.h"

#include "adc.h"

#ifdef SCREEN_MODE_MONO

/// package: passport

/// class Powermon:
///     """
///     Passport power monitor.
///     """
typedef struct _mp_obj_Powermon_t {
    mp_obj_base_t base;
    uint16_t      current;
    uint16_t      voltage;
} mp_obj_Powermon_t;

/// def __init__(self):
///     """
///     Initialize power monitor.
///     """
STATIC mp_obj_t mod_passport_Powermon_make_new(const mp_obj_type_t* type,
                                               size_t               n_args,
                                               size_t               n_kw,
                                               const mp_obj_t*      args) {
    mp_obj_Powermon_t* powermon = m_new_obj(mp_obj_Powermon_t);
    powermon->base.type         = type;
    powermon->current           = 0;
    powermon->voltage           = 0;

    return MP_OBJ_FROM_PTR(powermon);
}

/// def read(self) -> (int, int):
///     """
///     Read voltage and current as a tuple.
///     """
STATIC mp_obj_t mod_passport_Powermon_read(mp_obj_t self) {
    int      ret                = 0;
    uint16_t current            = 0;
    uint16_t voltage            = 0;
    mp_obj_t tuple[2]           = {0};
    mp_obj_Powermon_t* powermon = (mp_obj_Powermon_t*)self;

    if ((ret = adc_read_powermon(&current, &voltage)) < 0) {
        mp_raise_msg(&mp_type_RuntimeError, MP_ERROR_TEXT("Could not read voltage and current from power monitor"));
        return mp_const_none;
    }
    powermon->current = current;
    powermon->voltage = voltage;

    tuple[0] = mp_obj_new_int_from_uint(powermon->current);
    tuple[1] = mp_obj_new_int_from_uint(powermon->voltage);
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_Powermon_read_obj, mod_passport_Powermon_read);

STATIC const mp_rom_map_elem_t mod_passport_Powermon_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read),     MP_ROM_PTR(&mod_passport_Powermon_read_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_Powermon_locals_dict, mod_passport_Powermon_locals_dict_table);

const mp_obj_type_t mod_passport_Powermon_type = {
    {&mp_type_type},
    .name        = MP_QSTR_Powermon,
    .make_new    = mod_passport_Powermon_make_new,
    .locals_dict = (void*)&mod_passport_Powermon_locals_dict,
};

#endif