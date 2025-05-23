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

#ifdef USE_SECP256K1_ZKP_ECDSA
#include "zkp_ecdsa.h"
#endif


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

/// def (x1: bytes, y1: bytes, x2: bytes, y2: bytes) -> added_point: (bytes, bytes)
///     """
///     Add two ECDSA points
///     """
STATIC mp_obj_t mod_trezorcrypto_ecdsa_point_add(size_t n_args, const mp_obj_t * args) {

    // Build the points
    curve_point p1, p2;

    // Get the coordinates from their objects
    mp_buffer_info_t x1_buf;
    mp_get_buffer_raise(args[0], &x1_buf, MP_BUFFER_READ);

    mp_buffer_info_t y1_buf;
    mp_get_buffer_raise(args[1], &y1_buf, MP_BUFFER_READ);

    mp_buffer_info_t x2_buf;
    mp_get_buffer_raise(args[2], &x2_buf, MP_BUFFER_READ);

    mp_buffer_info_t y2_buf;
    mp_get_buffer_raise(args[3], &y2_buf, MP_BUFFER_READ);

    // Convert coordinates to bignums
    bn_read_be((uint8_t *)x1_buf.buf, &p1.x);
    bn_read_be((uint8_t *)y1_buf.buf, &p1.y);
    bn_read_be((uint8_t *)x2_buf.buf, &p2.x);
    bn_read_be((uint8_t *)y2_buf.buf, &p2.y);

    // Add
    point_add(&secp256k1, &p1, &p2);

    // Retrieve x and y bytes from output point
    vstr_t x_vstr, y_vstr;
    vstr_init_len(&x_vstr, 32);
    vstr_init_len(&y_vstr, 32);
    bn_write_be(&p2.x, (uint8_t *)x_vstr.buf);
    bn_write_be(&p2.y, (uint8_t *)y_vstr.buf);

    // Put x and y bytes in a tuple
    mp_obj_tuple_t * tuple = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
    tuple->items[0] = mp_obj_new_str_from_vstr(&mp_type_bytes, &x_vstr);
    tuple->items[1] = mp_obj_new_str_from_vstr(&mp_type_bytes, &y_vstr);
    return MP_OBJ_FROM_PTR(tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(
    mod_trezorcrypto_ecdsa_point_add_obj,
    4,
    4,
    mod_trezorcrypto_ecdsa_point_add);

/// def sign(
///     secret_key: bytes,
///     digest: bytes,
///     compressed: bool = True,
///     canonical: int | None = None,
/// ) -> bytes:
///     """
///     Uses secret key to produce the signature of the digest.
///     """
STATIC mp_obj_t mod_trezorcrypto_ecdsa_sign(size_t n_args,
                                                const mp_obj_t *args) {
  mp_buffer_info_t sk = {0};
  mp_buffer_info_t dig = {0};
  mp_get_buffer_raise(args[0], &sk, MP_BUFFER_READ);
  mp_get_buffer_raise(args[1], &dig, MP_BUFFER_READ);
  bool compressed = (n_args < 3) || (args[2] == mp_const_true);
  int (*is_canonical)(uint8_t by, uint8_t sig[64]) = NULL;
#if !BITCOIN_ONLY
  mp_int_t canonical = (n_args > 3) ? mp_obj_get_int(args[3]) : 0;
  switch (canonical) {
    case CANONICAL_SIG_ETHEREUM:
      is_canonical = ethereum_is_canonical;
      break;
    case CANONICAL_SIG_EOS:
      is_canonical = eos_is_canonical;
      break;
  }
#endif
  if (sk.len != 32) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of secret key"));
  }
  if (dig.len != 32) {
    mp_raise_ValueError(MP_ERROR_TEXT("Invalid length of digest"));
  }
  vstr_t sig = {0};
  vstr_init_len(&sig, 65);
  uint8_t pby = 0;
  int ret = 0;
#ifdef USE_SECP256K1_ZKP_ECDSA
  if (!is_canonical) {
    ret = zkp_ecdsa_sign_digest(&secp256k1, (const uint8_t *)sk.buf,
                                (const uint8_t *)dig.buf,
                                (uint8_t *)sig.buf + 1, &pby, is_canonical);
  } else
#endif
  {
    ret = ecdsa_sign_digest(&secp256k1, (const uint8_t *)sk.buf,
                            (const uint8_t *)dig.buf, (uint8_t *)sig.buf + 1,
                            &pby, is_canonical);
  }
  if (0 != ret) {
    vstr_clear(&sig);
    mp_raise_ValueError(MP_ERROR_TEXT("Signing failed"));
  }
  sig.buf[0] = 27 + pby + compressed * 4;
  return mp_obj_new_str_from_vstr(&mp_type_bytes, &sig);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_trezorcrypto_ecdsa_sign_obj,
                                           2, 4,
                                           mod_trezorcrypto_ecdsa_sign);

STATIC const mp_rom_map_elem_t mod_trezorcrypto_ecdsa_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_ecdsa)},
    {MP_ROM_QSTR(MP_QSTR_scalar_multiply),
     MP_ROM_PTR(&mod_trezorcrypto_ecdsa_scalar_multiply_obj)},
    {MP_ROM_QSTR(MP_QSTR_point_add),
     MP_ROM_PTR(&mod_trezorcrypto_ecdsa_point_add_obj)},
    {MP_ROM_QSTR(MP_QSTR_sign),
     MP_ROM_PTR(&mod_trezorcrypto_ecdsa_sign_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_trezorcrypto_ecdsa_globals,
                            mod_trezorcrypto_ecdsa_globals_table);

STATIC const mp_obj_module_t mod_trezorcrypto_ecdsa_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_trezorcrypto_ecdsa_globals,
};
