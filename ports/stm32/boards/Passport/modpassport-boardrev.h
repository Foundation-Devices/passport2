// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "py/runtime.h"

#include "adc.h"

/// package: passport

/// class Boardrev:
///     """
///     Passport PCB revision.
///     """
typedef struct _mp_obj_Boardrev_t {
    mp_obj_base_t base;
} mp_obj_Boardrev_t;

/// def __init__(self) -> None:
///     """
///     Initialize board revision object.
///     """
STATIC mp_obj_t mod_passport_Boardrev_make_new(const mp_obj_type_t* type,
                                               size_t               n_args,
                                               size_t               n_kw,
                                               const mp_obj_t*      args) {
    mp_obj_Boardrev_t* boardrev = m_new_obj(mp_obj_Boardrev_t);
    boardrev->base.type         = type;

    return MP_OBJ_FROM_PTR(boardrev);
}

/// def read(self) -> int:
///     """
///     Read board revision as an integer.
///     """
STATIC mp_obj_t mod_passport_Boardrev_read(mp_obj_t self) {
    int ret             = 0;
    uint16_t boardrev   = 0;

    if ((ret = adc_read_boardrev(&boardrev)) < 0) {
        mp_raise_msg(&mp_type_OverflowError, MP_ERROR_TEXT("Could not read board revision"));
        return mp_const_none;
    }
    return mp_obj_new_int_from_uint(boardrev);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_Boardrev_read_obj, mod_passport_Boardrev_read);

STATIC const mp_rom_map_elem_t mod_passport_Boardrev_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read),     MP_ROM_PTR(&mod_passport_Boardrev_read_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_Boardrev_locals_dict, mod_passport_Boardrev_locals_dict_table);

const mp_obj_type_t mod_passport_Boardrev_type = {
    {&mp_type_type},
    .name        = MP_QSTR_Boardrev,
    .make_new    = mod_passport_Boardrev_make_new,
    .locals_dict = (void*)&mod_passport_Boardrev_locals_dict,
};