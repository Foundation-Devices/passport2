// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundation.xyz>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"

#include "adc.h"
#include "noise.h"
#include "stm32h7xx_hal.h"

/// package: passport

/// class Noise:
///     """
///     """
typedef struct _mp_obj_Noise_t {
    mp_obj_base_t base;
} mp_obj_Noise_t;

/// def __init__(self) -> None:
///     """
///     Initialize noise generation object.
///     """
STATIC mp_obj_t mod_passport_Noise_make_new(const mp_obj_type_t* type,
                                            size_t               n_args,
                                            size_t               n_kw,
                                            const mp_obj_t*      args) {
    mp_obj_Noise_t* noise = m_new_obj(mp_obj_Noise_t);
    noise->base.type      = type;

    noise_enable();
    return MP_OBJ_FROM_PTR(noise);
}

/// def read(self) -> (int, int):
///     """
///     Read noise from the avalanche noise generator ADC inputs and return it
///     directly as a tuple of two ints.
///     """
STATIC mp_obj_t mod_passport_Noise_read(mp_obj_t self) {
    HAL_StatusTypeDef ret   = 0;
    uint32_t noise1         = 0;
    uint32_t noise2         = 0;
    mp_obj_t tuple[2]       = {0};

    if ((ret = adc_read_noise_inputs(&noise1, &noise2)) < 0) {
        return mp_const_none;
    }

    tuple[0] = mp_obj_new_int_from_uint(noise1);
    tuple[1] = mp_obj_new_int_from_uint(noise2);
    return mp_obj_new_tuple(2, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_Noise_read_obj, mod_passport_Noise_read);

/// def random_bytes(self, buf: buffer, sources: int) -> (int, int):
///     """
///     Read random bytes from multiple noise sources.
///     """
STATIC mp_obj_t mod_passport_Noise_random_bytes(mp_obj_t self,
                                                mp_obj_t buf_obj,
                                                mp_obj_t sources_obj) {
    mp_buffer_info_t buf_info   = {0};
    mp_int_t sources            = 0;

    mp_get_buffer_raise(buf_obj, &buf_info, MP_BUFFER_WRITE);
    sources = mp_obj_get_int(sources_obj);

    if (!noise_get_random_bytes(sources, buf_info.buf, buf_info.len)) {
        return mp_const_false;
    }

    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_Noise_random_bytes_obj, mod_passport_Noise_random_bytes);

/// def __del__(self) -> None:
///     """
///     """
STATIC mp_obj_t mod_passport_Noise___del__(mp_obj_t self) {
    noise_disable();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_Noise___del___obj, mod_passport_Noise___del__);

STATIC const mp_rom_map_elem_t mod_passport_Noise_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_AVALANCHE),    MP_ROM_INT(NOISE_AVALANCHE_SOURCE)},
    {MP_ROM_QSTR(MP_QSTR_MCU),          MP_ROM_INT(NOISE_MCU_RNG_SOURCE)},
    {MP_ROM_QSTR(MP_QSTR_SE),           MP_ROM_INT(NOISE_SE_RNG_SOURCE)},
    {MP_ROM_QSTR(MP_QSTR_ALL),          MP_ROM_INT(NOISE_ALL)},
    {MP_ROM_QSTR(MP_QSTR_read),         MP_ROM_PTR(&mod_passport_Noise_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_random_bytes), MP_ROM_PTR(&mod_passport_Noise_random_bytes_obj)},
    {MP_ROM_QSTR(MP_QSTR___del__),      MP_ROM_PTR(&mod_passport_Noise___del___obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_Noise_locals_dict, mod_passport_Noise_locals_dict_table);

const mp_obj_type_t mod_passport_Noise_type = {
    {&mp_type_type},
    .name        = MP_QSTR_Noise,
    .make_new    = mod_passport_Noise_make_new,
    .locals_dict = (void*)&mod_passport_Noise_locals_dict,
};