/*
 * This file is part of the TREZOR project, https://trezor.io/
 *
 * Copyright (c) SatoshiLabs
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 *
 * This program is distributed in the hope that it will be useful,
 * but WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 * GNU General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program.  If not, see <http://www.gnu.org/licenses/>.
 */

#include <string.h>

#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"

#include "secp256k1.h"
#include "ecdsa.h"

#define  X_SIZE 32

/// package: trezorcrypto.ecdsa

/// def get_x(pubkey: bytes) -> bytes:
///     """
///     Gets the X coordinate of the point corresponding to an ECDSA pubkey
///     """
STATIC mp_obj_t mod_trezorcrypto_ecdsa_get_x(mp_obj_t pubkey_obj) {
    mp_buffer_info_t pubkey;
    mp_get_buffer_raise(pubkey_obj, &pubkey, MP_BUFFER_READ);

    vstr_t x_vstr;
    vstr_init_len(&x_vstr, X_SIZE);
    x_vstr.len = X_SIZE;

    int rv = ecdsa_get_x(&secp256k1, pubkey.buf, (uint8_t *)x_vstr.buf);
    if (rv == 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("failed to get x"));
    }

    return mp_obj_new_str_from_vstr(&mp_type_bytes, &x_vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_ecdsa_get_x_obj,
    mod_trezorcrypto_ecdsa_get_x);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_ecdsa_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ecdsa)},
    {MP_ROM_QSTR(MP_QSTR_get_x),
     MP_ROM_PTR(&mod_trezorcrypto_ecdsa_get_x_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_ecdsa_globals,
                            mod_trezorcrypto_ecdsa_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_ecdsa_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_ecdsa_globals,
};
