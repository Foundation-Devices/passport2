// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "foundation.h"

/// package: foundation.ur

STATIC const mp_obj_type_t mod_foundation_spi_Spi_type;

/// class Spi():
///     """
///     """
typedef struct _mp_obj_Spi_t {
    mp_obj_base_t base;
    SPI_Flash_t;
} mp_obj_Spi_t;


/// def __init__(self, index: int) -> None:
///     """
///     """
STATIC mp_obj_t mod_foundation_spi_Spi_make_new(const mp_obj_type_t *type,
                                                size_t n_args,
                                                size_t n_kw,
                                                const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 1, 1, false);

    mp_obj_Spi_t *o = m_new_obj(mp_obj_Spi_t);
    o->base.type = &mod_foundation_spi_Spi_type;

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_rom_map_elem_t mod_foundation_spi_Spi_locals_dict_table[] = {
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_spi_Spi_locals_dict, mod_foundation_spi_Spi_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_spi_Spi_type = {
    { &mp_type_type },
    .name = MP_QSTR_Spi,
    .make_new = mod_foundation_spi_Spi_make_new,
    .locals_dict = (mp_obj_dict_t *)&mod_foundation_spi_Spi_locals_dict,
};

STATIC const mp_rom_map_elem_t mod_foundation_spi_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_Spi), MP_ROM_PTR(&mod_foundation_spi_Spi_type)},
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_spi_globals, mod_foundation_spi_globals_table);

STATIC const mp_obj_module_t mod_foundation_spi_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_spi_globals,
};
