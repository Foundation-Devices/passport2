// SPDX-FileCopyrightText: © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "foundation.h"

/// def public_key(secret_key) -> bytes:
STATIC mp_obj_t mod_foundation_secp256k1_public_key_schnorr(mp_obj_t secret_key_obj)
{
    uint8_t public_key[32];
    mp_buffer_info_t secret_key;

    mp_get_buffer_raise(secret_key_obj, &secret_key, MP_BUFFER_READ);
    if (secret_key.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("secret key should be 32 bytes"));
    }

    foundation_secp256k1_public_key_schnorr(secret_key.buf, &public_key);
    return mp_obj_new_bytes(public_key, 32);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_secp256k1_public_key_schnorr_obj,
                                 mod_foundation_secp256k1_public_key_schnorr);

/// def sign_ecdsa(data, secret_key) -> bytes:
STATIC mp_obj_t mod_foundation_secp256k1_sign_ecdsa(mp_obj_t data_obj,
                                                    mp_obj_t secret_key_obj)
{
    mp_buffer_info_t data;
    mp_buffer_info_t secret_key;
    uint8_t signature[64];

    mp_get_buffer_raise(data_obj, &data, MP_BUFFER_READ);
    mp_get_buffer_raise(secret_key_obj, &secret_key, MP_BUFFER_READ);

    if (data.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("data should be 32 bytes"));
    }

    if (secret_key.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("secret key should be 32 bytes"));
    }

    foundation_secp256k1_sign_ecdsa(data.buf,
                                    secret_key.buf,
                                    &signature);

    return mp_obj_new_bytes(signature, sizeof(signature));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_secp256k1_sign_ecdsa_obj,
                                 mod_foundation_secp256k1_sign_ecdsa);

/// def sign_ecdsa_recoverable(data, secret_key) -> (bytes, recovery_id):
STATIC mp_obj_t mod_foundation_secp256k1_sign_ecdsa_recoverable(mp_obj_t data_obj,
                                                    mp_obj_t secret_key_obj)
{
    mp_buffer_info_t data;
    mp_buffer_info_t secret_key;
    uint8_t signature[64];
    int8_t recovery_id;

    mp_get_buffer_raise(data_obj, &data, MP_BUFFER_READ);
    mp_get_buffer_raise(secret_key_obj, &secret_key, MP_BUFFER_READ);

    if (data.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("data should be 32 bytes"));
    }

    if (secret_key.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("secret key should be 32 bytes"));
    }

    foundation_secp256k1_sign_ecdsa_recoverable(data.buf,
                                                secret_key.buf,
                                                &signature,
                                                &recovery_id);

    mp_obj_tuple_t * signature_data = MP_OBJ_TO_PTR(mp_obj_new_tuple(2, NULL));
    signature_data->items[0] = mp_obj_new_bytes(signature, sizeof(signature));
    signature_data->items[1] = mp_obj_new_int(recovery_id);

    return MP_OBJ_FROM_PTR(signature_data);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_secp256k1_sign_ecdsa_recoverable_obj,
                                 mod_foundation_secp256k1_sign_ecdsa_recoverable);

/// def sign_schnorr(data, secret_key) -> bytes:
///     """
///     """
STATIC mp_obj_t mod_foundation_secp256k1_sign_schnorr(mp_obj_t data_obj,
                                                      mp_obj_t secret_key_obj)
{
    mp_buffer_info_t data;
    mp_buffer_info_t secret_key;
    uint8_t signature[64];

    mp_get_buffer_raise(data_obj, &data, MP_BUFFER_READ);
    mp_get_buffer_raise(secret_key_obj, &secret_key, MP_BUFFER_READ);

    if (data.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("data should be 32 bytes"));
    }

    if (secret_key.len != 32) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("secret key should be 32 bytes"));
    }

    foundation_secp256k1_sign_schnorr(data.buf,
                                      secret_key.buf,
                                      &signature);

    return mp_obj_new_bytes(signature, sizeof(signature));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_secp256k1_sign_schnorr_obj,
                                 mod_foundation_secp256k1_sign_schnorr);

STATIC const mp_rom_map_elem_t mod_foundation_secp256k1_globals_table[] = {
    { MP_ROM_QSTR(MP_QSTR_public_key_schnorr), MP_ROM_PTR(&mod_foundation_secp256k1_public_key_schnorr_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign_ecdsa), MP_ROM_PTR(&mod_foundation_secp256k1_sign_ecdsa_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign_ecdsa_recoverable), MP_ROM_PTR(&mod_foundation_secp256k1_sign_ecdsa_recoverable_obj) },
    { MP_ROM_QSTR(MP_QSTR_sign_schnorr), MP_ROM_PTR(&mod_foundation_secp256k1_sign_schnorr_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_secp256k1_globals, mod_foundation_secp256k1_globals_table);

STATIC const mp_obj_module_t mod_foundation_secp256k1_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_secp256k1_globals,
};
