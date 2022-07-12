// SPDX-FileCopyrightText: 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// MP C foundation module, supports LCD, backlight, keypad and other devices as they are added
//
// This code is shared between the Passport hardware build and the unix simulator build.
// No hardware-specific code should be added to this file.

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"

// QRCode includes
#include "qrcode.h"

#include "image_conversion.h"

#include "hash.h"
#include "firmware-keys.h"

#include "sha256.h"
#include "uECC.h"
#include "utils.h"

#include "modfoundation-bip39.h"
#include "modfoundation-qr.h"

/// package: foundation

/// class QRCode:
typedef struct _mp_obj_QRCode_t
{
    mp_obj_base_t base;
    QRCode code;
} mp_obj_QRCode_t;

// We only have versions here that can be rendered on Pasport's display
STATIC uint16_t version_capacity_alphanumeric[] = {
    25,   // 1
    47,   // 2
    77,   // 3
    114,  // 4
    154,  // 5
    195,  // 6
    224,  // 7
    279,  // 8
    335,  // 9
    395,  // 10
    468,  // 11
    535,  // 12
    619,  // 13
    667,  // 14
    758,  // 15
    854,  // 16
    938,  // 17
    1046, // 18
    1153, // 19
    1249, // 20
    1352, // 21
    1460, // 22
    1588, // 23
    1704  // 24
};

STATIC uint16_t version_capacity_binary[] = {
    17,   // 1
    32,   // 2
    53,   // 3
    78,   // 4
    106,  // 5
    134,  // 6
    154,  // 7
    192,  // 8
    230,  // 9
    271,  // 10
    321,  // 11
    367,  // 12
    425,  // 13
    458,  // 14
    520,  // 15
    586,  // 16
    644,  // 17
    718,  // 18
    792,  // 19
    858,  // 20
    929,  // 21
    1003, // 22
    1091, // 23
    1171  // 24
};

/// def __init__(self, mode: int, key: bytes, iv: bytes = None) -> boolean:
///     '''
///     Initialize QRCode context.
///     '''
STATIC mp_obj_t QRCode_make_new(const mp_obj_type_t *type, size_t n_args, size_t n_kw, const mp_obj_t *args)
{
    mp_obj_QRCode_t *o = m_new_obj(mp_obj_QRCode_t);
    o->base.type = type;
    return MP_OBJ_FROM_PTR(o);
}

QRCode qrcode;
#define QRCODE_DEBUG

/// def render(self) -> None
///     '''
///     Render a QR code with the given data, version and ecc level
///     '''
STATIC mp_obj_t QRCode_render(size_t n_args, const mp_obj_t *args)
{
    mp_check_self(mp_obj_is_str_or_bytes(args[1]));
    GET_STR_DATA_LEN(args[1], text_str, text_len);

    uint8_t version = mp_obj_get_int(args[2]);
    uint8_t ecc = mp_obj_get_int(args[3]);

    mp_buffer_info_t output_info;
    mp_get_buffer_raise(args[4], &output_info, MP_BUFFER_WRITE);

    uint8_t result = qrcode_initBytes(&qrcode, (uint8_t *)output_info.buf, version, ecc, (uint8_t *)text_str, text_len);

    return result == 0 ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(QRCode_render_obj, 5, 5, QRCode_render);

/// def fit_to_version(self) -> None
///     '''
///    Return the QR code version that best fits this data (assumes ECC level 0 for now)
///     '''
STATIC mp_obj_t QRCode_fit_to_version(mp_obj_t self, mp_obj_t data_size, mp_obj_t is_alphanumeric)
{
    uint16_t size = mp_obj_get_int(data_size);
    uint16_t is_alpha = mp_obj_get_int(is_alphanumeric);
    uint16_t *lookup_table = is_alpha ? version_capacity_alphanumeric : version_capacity_binary;

    int num_entries = sizeof(version_capacity_alphanumeric) / sizeof(uint16_t);

    for (int i = 0; i < num_entries; i++)
    {
        if (lookup_table[i] >= size)
        {
            return mp_obj_new_int(i + 1);
        }
    }

    // Data is too big
    return mp_obj_new_int(0);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(QRCode_fit_to_version_obj, QRCode_fit_to_version);

STATIC const mp_rom_map_elem_t QRCode_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_render), MP_ROM_PTR(&QRCode_render_obj)},
    {MP_ROM_QSTR(MP_QSTR_fit_to_version), MP_ROM_PTR(&QRCode_fit_to_version_obj)},
};
STATIC MP_DEFINE_CONST_DICT(QRCode_locals_dict, QRCode_locals_dict_table);

STATIC const mp_obj_type_t QRCode_type = {
    {&mp_type_type},
    .name = MP_QSTR_QRCode,
    .make_new = QRCode_make_new,
    .locals_dict = (void *)&QRCode_locals_dict,
};

/// def convert_rgb565_to_grayscale(rgb565: bytearray,
///                                 grayscale: bytearray,
///                                 hor_res: int,
///                                 ver_res: int) -> None:
///     '''
///     Convert the given RGB565 image to grayscale for QR search.
///     '''
STATIC mp_obj_t mod_foundation_convert_rgb565_to_grayscale(size_t n_args, const mp_obj_t *args)
{
    mp_buffer_info_t rgb565_info;
    mp_get_buffer_raise(args[0], &rgb565_info, MP_BUFFER_READ);

    mp_buffer_info_t grayscale_info;
    mp_get_buffer_raise(args[1], &grayscale_info, MP_BUFFER_WRITE);

    mp_int_t hor_res = mp_obj_get_int(args[2]);
    mp_int_t ver_res = mp_obj_get_int(args[3]);

    if (rgb565_info.len != (hor_res * ver_res * sizeof(uint16_t)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid rgb565 buffer size"));
        return mp_const_none;
    }
    if (grayscale_info.len != (hor_res * ver_res))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid grayscale buffer size"));
        return mp_const_none;
    }

    convert_rgb565_to_grayscale(rgb565_info.buf, grayscale_info.buf, hor_res, ver_res);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_foundation_convert_rgb565_to_grayscale_obj,
                                           4,
                                           4,
                                           mod_foundation_convert_rgb565_to_grayscale);

/// def sha256(buffer, digest: bytearray) -> None
///     '''
///     Perform a sha256 hash on the given data (bytearray)
///     '''
STATIC mp_obj_t mod_foundation_sha256(mp_obj_t data, mp_obj_t digest)
{
    mp_buffer_info_t data_info;
    mp_get_buffer_raise(data, &data_info, MP_BUFFER_READ);

    mp_buffer_info_t digest_info;
    mp_get_buffer_raise(digest, &digest_info, MP_BUFFER_WRITE);

    if (digest_info.len != SHA256_BLOCK_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid digest bytearray len"));
        return mp_const_none;
    }

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, (void *)data_info.buf, data_info.len);
    sha256_final(&ctx, digest_info.buf);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_sha256_obj, mod_foundation_sha256);

/*
 * Add additional class local dictionary table and data structure here
 * And add the Class name and MP_ROM_PTR() to the globals table
 * below
 */

/* Module Global configuration */
/* Define all properties of the module.
 * Table entries are key/value pairs of the attribute name (a string)
 * and the MicroPython object reference.
 * All identifiers and strings are written as MP_QSTR_xxx and will be
 * optimized to word-sized integers by the build system (interned strings).
 */

STATIC const mp_rom_map_elem_t foundation_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_foundation)},
    {MP_ROM_QSTR(MP_QSTR_bip39), MP_ROM_PTR(&mod_foundation_bip39_module)},
    {MP_ROM_QSTR(MP_QSTR_qr), MP_ROM_PTR(&mod_foundation_qr_module)},
    {MP_ROM_QSTR(MP_QSTR_QRCode), MP_ROM_PTR(&QRCode_type)},
    {MP_ROM_QSTR(MP_QSTR_convert_rgb565_to_grayscale), MP_ROM_PTR(&mod_foundation_convert_rgb565_to_grayscale_obj)},
    {MP_ROM_QSTR(MP_QSTR_sha256), MP_ROM_PTR(&mod_foundation_sha256_obj)},
};
STATIC MP_DEFINE_CONST_DICT(foundation_module_globals, foundation_module_globals_table);

/* Define module object. */
const mp_obj_module_t foundation_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&foundation_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_foundation, foundation_user_cmodule, PASSPORT_FOUNDATION_ENABLED);
