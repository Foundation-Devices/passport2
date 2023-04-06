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

#include "schnorr.h"
#include "secp256k1.h"

/// package: trezorcrypto.schnorr

/// def sign(pk: bytes, digest: bytes) -> bytes:
///     """
///     Schnorr signatures
///     """
STATIC mp_obj_t mod_trezorcrypto_schnorr_sign(mp_obj_t pk_obj, mp_obj_t digest_obj) {
    mp_buffer_info_t pk, digest;
    mp_get_buffer_raise(pk_obj, &pk, MP_BUFFER_READ);
    mp_get_buffer_raise(digest_obj, &digest, MP_BUFFER_READ);

    vstr_t signature;
    vstr_init_len(&signature, SCHNORR_SIG_LENGTH);

    int rv = schnorr_sign_digest(&secp256k1, pk.buf, digest.buf, (uint8_t *)signature.buf);
    if (rv != 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("schnorr signature failed"));
    }
    signature.len = strlen(signature.buf);

    return mp_obj_new_str_from_vstr(&mp_type_str, &signature);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(
    mod_trezorcrypto_schnorr_sign_obj,
    mod_trezorcrypto_schnorr_sign);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_schnorr_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_schnorr)},
    {MP_ROM_QSTR(MP_QSTR_sign),
     MP_ROM_PTR(&mod_trezorcrypto_schnorr_sign_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_schnorr_globals,
                            mod_trezorcrypto_schnorr_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_schnorr_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_schnorr_globals,
};
