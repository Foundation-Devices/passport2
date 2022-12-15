// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <stdint.h>

#include "py/obj.h"
#include "py/objarray.h"

#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

#include "framebuffer.h"

/**
 * @brief Attribute used to allocate a static variable in the
 *        DTCM section.
 */
#define MP_DTCM __attribute__((section(".dtcm")))

/**
 * @brief Create a compile-time bytearray by reference.
 *
 * Same behaviour as `mp_obj_new_bytearray_by_ref` (bytearray_at in Python side)
 * but statically allocated.
 *
 * @param obj The object name.
 * @param ptr The pointer to the data.
 * @param len The length of the data.
 */
#define MP_OBJ_BYTEARRAY_BY_REF(obj, ptr, ptr_len)  \
    mp_obj_array_t obj = {                          \
        .base = {&mp_type_bytearray},               \
        .typecode = BYTEARRAY_TYPECODE,             \
        .free = 0,                                  \
        .len = ptr_len,                             \
        .items = ptr,                               \
    }

/// package: passport.dtcm

/// qr_workloads_buf: bytearray
// TODO: make constants for max_workloads and max_workload_size
STATIC MP_DTCM uint8_t mod_passport_dtcm_qr_workdloads_buf[16 * 768];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_dtcm_qr_workdloads_buf_obj,
                               mod_passport_dtcm_qr_workdloads_buf,
                               sizeof(mod_passport_dtcm_qr_workdloads_buf));

STATIC const mp_rom_map_elem_t mod_passport_dtcm_globals_table[] = {
        {MP_ROM_QSTR(MP_QSTR_qr_workloads_buf), MP_ROM_PTR(&mod_passport_dtcm_qr_workdloads_buf_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_dtcm_globals, mod_passport_dtcm_globals_table);

STATIC const mp_obj_module_t mod_passport_dtcm_module = {
        .base    = {&mp_type_module},
        .globals = (mp_obj_dict_t*)&mod_passport_dtcm_globals,
};
