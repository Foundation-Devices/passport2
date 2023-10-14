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

#include "ecdsa.h"
#include "secp256k1.h"
#include "bignum.h"


/// package: trezorcrypto.ecdsa

/// def (k: bytes) -> multiplied_point: (bytes, bytes)
///     """
///     Multiply a scalar by the generator point G
///     """
STATIC mp_obj_t mod_trezorcrypto_ecdsa_scalar_multiply(mp_obj_t k_obj) {

    // Get k from object
    mp_buffer_info_t k_buf;
    mp_get_buffer_raise(k_obj, &k_buf, MP_BUFFER_READ);

    // Convert k to a bignum
    bignum256 k;
    bn_read_be((uint8_t *)k_buf.buf, &k);

    // Multiply
    curve_point output;
    int rv = scalar_multiply(&secp256k1, &k, &output);
    if (rv != 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("scalar multiply failed"));
    }

    // Retrieve x and y bytes from output point
    vstr_t x_vstr, y_vstr;
    vstr_init_len(&x_vstr, 32);
    vstr_init_len(&y_vstr, 32);
    bn_write_be(&output.x, (uint8_t *)x_vstr.buf);
    bn_write_be(&output.y, (uint8_t *)y_vstr.buf);

    // Put x and y bytes in a tuple
    mp_obj_tuple_t * tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
    tuple->items[0] = mp_obj_new_str_from_vstr(&mp_type_bytes, &x_vstr);
    tuple->items[1] = mp_obj_new_str_from_vstr(&mp_type_bytes, &y_vstr);
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(
    mod_trezorcrypto_ecdsa_scalar_multiply_obj,
    mod_trezorcrypto_ecdsa_scalar_multiply);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_ecdsa_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ecdsa)},
    {MP_ROM_QSTR(MP_QSTR_scalar_multiply),
     MP_ROM_PTR(&mod_trezorcrypto_ecdsa_scalar_multiply_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_ecdsa_globals,
                            mod_trezorcrypto_ecdsa_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_ecdsa_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_ecdsa_globals,
};
