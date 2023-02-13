// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
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

#include "image_conversion.h"

#include "hash.h"
#include "firmware-keys.h"

#include "sha256.h"
#include "uECC.h"
#include "utils.h"

#include "modfoundation-bip39.h"
#include "modfoundation-qr.h"
#include "modfoundation-ur.h"

/// package: foundation

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
    {MP_ROM_QSTR(MP_QSTR_ur), MP_ROM_PTR(&mod_foundation_ur_module)},
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
