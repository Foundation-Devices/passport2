
// SPDX-FileCopyrightText:  © 2023 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later

#include <string.h>
#include "py/obj.h"
#include "foundation.h"

/// package: foundation.ur

STATIC const mp_obj_type_t mod_foundation_ur_Value_type;
STATIC const mp_obj_type_t mod_foundation_ur_CoinType_type;
STATIC const mp_obj_type_t mod_foundation_ur_CryptoCoinInfo_type;
STATIC const mp_obj_type_t mod_foundation_ur_CryptoKeypath_type;
STATIC const mp_obj_type_t mod_foundation_ur_PassportRequest_type;

STATIC struct _mp_obj_PassportRequest_t *mod_foundation_ur_PassportRequest_new(UR_PassportRequest *value);

/// class Value:
///     """
///     """
typedef struct _mp_obj_Value_t {
    mp_obj_base_t base;
    UR_Value value;
} mp_obj_Value_t;


/// def __str__(self) -> str:
///     """
///     """
STATIC void mod_foundation_ur_Value_print(const mp_print_t *print,
                                          mp_obj_t o_in,
                                          mp_print_kind_t kind) {
    (void) kind;

    mp_obj_Value_t *o = MP_OBJ_TO_PTR(o_in);

    switch (o->value.tag) {
        case Bytes:
            mp_print_str(print, "UR_Value::Bytes");
            break;
        case CryptoHDKey:
            mp_print_str(print, "UR_Value::CryptoHDKey");
            break;
        case CryptoPSBT:
            mp_print_str(print, "UR_Value::CryptoPSBT");
            break;
        case PassportRequest:
            mp_print_str(print, "UR_Value::PassportRequest");
            break;
        default:
            mp_print_str(print, "Unknown");
            break;
    }
}

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_Value_t *mod_foundation_ur_Value_new(UR_Value *value) {
    mp_obj_Value_t *o = m_new_obj(mp_obj_Value_t);
    o->base.type = &mod_foundation_ur_Value_type;
    memcpy(&o->value, value, sizeof(UR_Value));
    return o;
}

/// def ur_type(self) -> str:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_Value_ur_type(mp_obj_t self_in) {
    mp_obj_Value_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_int(self->value.tag);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_Value_ur_type_obj, mod_foundation_ur_Value_ur_type);

/// def unwrap_bytes(self) -> bytearray:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_Value_unwrap_bytes(mp_obj_t self_in) {
    mp_obj_Value_t *self = MP_OBJ_TO_PTR(self_in);
    mp_check_self(self->value.tag == Bytes);
    return mp_obj_new_bytearray_by_ref(self->value.bytes.len, (void *)self->value.bytes.data);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_Value_unwrap_bytes_obj,
                                 mod_foundation_ur_Value_unwrap_bytes);

/// def unwrap_crypto_psbt(self) -> bytearray:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_Value_unwrap_crypto_psbt(mp_obj_t self_in) {
    mp_obj_Value_t *self = MP_OBJ_TO_PTR(self_in);
    mp_check_self(self->value.tag == CryptoPSBT);

    return mp_obj_new_bytearray_by_ref(self->value.crypto_psbt.len, (void *)self->value.crypto_psbt.data);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_Value_unwrap_crypto_psbt_obj,
                                 mod_foundation_ur_Value_unwrap_crypto_psbt);

/// def unwrap_passport_request(self) -> PassportRequest:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_Value_unwrap_passport_request(mp_obj_t self_in) {
    mp_obj_Value_t *self = MP_OBJ_TO_PTR(self_in);
    mp_check_self(self->value.tag == PassportRequest);

    return MP_OBJ_FROM_PTR(mod_foundation_ur_PassportRequest_new(&self->value.passport_request));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_Value_unwrap_passport_request_obj,
                                 mod_foundation_ur_Value_unwrap_passport_request);

STATIC const mp_rom_map_elem_t mod_foundation_ur_Value_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_BYTES), MP_ROM_INT(Bytes) },
    { MP_ROM_QSTR(MP_QSTR_CRYPTO_HDKEY), MP_ROM_INT(CryptoHDKey) },
    { MP_ROM_QSTR(MP_QSTR_CRYPTO_PSBT), MP_ROM_INT(CryptoPSBT) },
    { MP_ROM_QSTR(MP_QSTR_PASSPORT_REQUEST), MP_ROM_INT(PassportRequest) },

    { MP_ROM_QSTR(MP_QSTR_ur_type), MP_ROM_PTR(&mod_foundation_ur_Value_ur_type_obj) },
    { MP_ROM_QSTR(MP_QSTR_unwrap_bytes), MP_ROM_PTR(&mod_foundation_ur_Value_unwrap_bytes_obj) },
    { MP_ROM_QSTR(MP_QSTR_unwrap_crypto_psbt), MP_ROM_PTR(&mod_foundation_ur_Value_unwrap_crypto_psbt_obj) },
    { MP_ROM_QSTR(MP_QSTR_unwrap_passport_request), MP_ROM_PTR(&mod_foundation_ur_Value_unwrap_passport_request_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_ur_Value_locals_dict, mod_foundation_ur_Value_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_ur_Value_type = {
    { &mp_type_type },
    .name = MP_QSTR_Value,
    .print = mod_foundation_ur_Value_print,
    .locals_dict = (mp_obj_dict_t *)&mod_foundation_ur_Value_locals_dict,
};

/// class CoinType:
///     """
///     """
///
///     BTC = 0
STATIC const mp_rom_map_elem_t mod_foundation_ur_CoinType_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_BTC), MP_ROM_INT(BTC) },
};

STATIC MP_DEFINE_CONST_DICT(mod_foundation_ur_CoinType_locals_dict,
                            mod_foundation_ur_CoinType_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_ur_CoinType_type = {
    { &mp_type_type },
    .name = MP_QSTR_CoinType,
    .locals_dict = (mp_obj_dict_t*)&mod_foundation_ur_CoinType_locals_dict,
};

/// class CryptoCoinInfo:
///     """
///     """
typedef struct _mp_obj_CryptoCoinInfo_t {
    mp_obj_base_t base;
    UR_CryptoCoinInfo info;
} mp_obj_CryptoCoinInfo_t;

STATIC mp_obj_t mod_foundation_ur_CryptoCoinInfo_make_new(const mp_obj_type_t *type,
                                                                size_t n_args,
                                                                size_t n_kw,
                                                                const mp_obj_t *args) {
    mp_arg_check_num(n_args, n_kw, 2, 2, false);

    mp_obj_CryptoCoinInfo_t *o = m_new_obj(mp_obj_CryptoCoinInfo_t);
    o->base.type = &mod_foundation_ur_CryptoCoinInfo_type;

    o->info.coin_type = mp_obj_get_int(args[0]);
    o->info.network = mp_obj_get_int(args[1]);

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_obj_type_t mod_foundation_ur_CryptoCoinInfo_type = {
    { &mp_type_type },
    .name = MP_QSTR_CryptoCoinInfo,
    .make_new = mod_foundation_ur_CryptoCoinInfo_make_new,
};

/// class CryptoKeypath:
///     """
///     """
typedef struct _mp_obj_CryptoKeypath_t {
    mp_obj_base_t base;
    UR_CryptoKeypath keypath;
} mp_obj_CryptoKeypath_t;

STATIC mp_obj_t mod_foundation_ur_CryptoKeypath_make_new(const mp_obj_type_t *type,
                                                         size_t n_args,
                                                         size_t n_kw,
                                                         const mp_obj_t *all_args) {
    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_source_fingerprint, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_depth,              MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all_kw_array(n_args, n_kw, all_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_obj_CryptoKeypath_t *o = m_new_obj(mp_obj_CryptoKeypath_t);
    o->base.type = &mod_foundation_ur_CryptoKeypath_type;

    if (args[0].u_obj != MP_OBJ_NULL) {
        o->keypath.source_fingerprint = mp_obj_get_int(args[0].u_obj);
    } else {
        o->keypath.source_fingerprint = 0;
    }

    if (args[1].u_obj != MP_OBJ_NULL) {
        o->keypath.depth = mp_obj_get_int(args[1].u_obj);
        o->keypath.has_depth = true;
    } else {
        o->keypath.depth = 0;
        o->keypath.has_depth = false;
    }

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_obj_type_t mod_foundation_ur_CryptoKeypath_type = {
    { &mp_type_type },
    .name = MP_QSTR_CryptoKeypath,
    .make_new = mod_foundation_ur_CryptoKeypath_make_new,
};

/// class PassportRequest:
///     """
///     """
typedef struct _mp_obj_PassportRequest_t {
    mp_obj_base_t base;
    UR_PassportRequest passport_request;
} mp_obj_PassportRequest_t;

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_PassportRequest_t *mod_foundation_ur_PassportRequest_new(UR_PassportRequest *passport_request) {
    mp_obj_PassportRequest_t *o = m_new_obj(mp_obj_PassportRequest_t);
    o->base.type = &mod_foundation_ur_PassportRequest_type;
    memcpy(&o->passport_request, passport_request, sizeof(UR_PassportRequest));
    return o;
}

STATIC mp_obj_t mod_foundation_ur_PassportRequest_uuid(mp_obj_t self_in)
{
    mp_obj_PassportRequest_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_bytes(self->passport_request.transaction_id, 16);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_PassportRequest_uuid_obj,
                                 mod_foundation_ur_PassportRequest_uuid);

STATIC mp_obj_t mod_foundation_ur_PassportRequest_scv_challenge_id(mp_obj_t self_in)
{
    mp_check_self(self->passport_request.has_scv_challenge);
    mp_obj_PassportRequest_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_bytes(self->passport_request.scv_challenge.id, 32);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_PassportRequest_scv_challenge_id_obj,
                                 mod_foundation_ur_PassportRequest_scv_challenge_id);

STATIC mp_obj_t mod_foundation_ur_PassportRequest_scv_challenge_signature(mp_obj_t self_in)
{
    mp_check_self(self->passport_request.has_scv_challenge);
    mp_obj_PassportRequest_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_bytes(self->passport_request.scv_challenge.signature, 64);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_PassportRequest_scv_challenge_signature_obj,
                                 mod_foundation_ur_PassportRequest_scv_challenge_signature);

STATIC const mp_rom_map_elem_t mod_foundation_ur_PassportRequest_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_uuid), MP_ROM_PTR(&mod_foundation_ur_PassportRequest_uuid_obj) },
    { MP_ROM_QSTR(MP_QSTR_scv_challenge_id), MP_ROM_PTR(&mod_foundation_ur_PassportRequest_scv_challenge_id_obj) },
    { MP_ROM_QSTR(MP_QSTR_scv_challenge_signature), MP_ROM_PTR(&mod_foundation_ur_PassportRequest_scv_challenge_signature_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_ur_PassportRequest_locals_dict,
                            mod_foundation_ur_PassportRequest_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_ur_PassportRequest_type = {
    { &mp_type_type },
    .name = MP_QSTR_PassportRequest,
    .locals_dict = (mp_obj_dict_t*)&mod_foundation_ur_PassportRequest_locals_dict,
};

/// def new_bytes(data: bytes) -> Value:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_new_bytes(mp_obj_t data_in)
{
    mp_buffer_info_t data = {0};
    UR_Value value;

    mp_get_buffer_raise(data_in, &data, MP_BUFFER_READ);
    ur_registry_new_bytes(&value, data.buf, data.len);
    return MP_OBJ_FROM_PTR(mod_foundation_ur_Value_new(&value));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_new_bytes_obj,
                                 mod_foundation_ur_new_bytes);

/// def new_derived_key(key_data=None,
///                     is_private=False,
///                     chain_code=None,
///                     use_info=None,
///                     parent_fingerprint=None) -> Value:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_new_derived_key(size_t n_args,
                                                  const mp_obj_t *pos_args,
                                                  mp_map_t *kw_args)
{
    mp_buffer_info_t key_data = {0};
    mp_buffer_info_t chain_code_info = {0};
    mp_obj_CryptoCoinInfo_t *use_info_obj = NULL;
    mp_obj_CryptoKeypath_t *origin_obj = NULL;
    UR_Value value = {0};

    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_key_data,           MP_ARG_REQUIRED | MP_ARG_OBJ,  {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_is_private,         MP_ARG_KW_ONLY  | MP_ARG_BOOL, {.u_bool = false} },
        { MP_QSTR_chain_code,         MP_ARG_KW_ONLY  | MP_ARG_OBJ,  {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_use_info,           MP_ARG_KW_ONLY  | MP_ARG_OBJ,  {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_origin,             MP_ARG_KW_ONLY  | MP_ARG_OBJ,  {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_parent_fingerprint, MP_ARG_KW_ONLY  | MP_ARG_INT,  {.u_int = 0} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_get_buffer_raise(args[0].u_obj, &key_data, MP_BUFFER_READ);
    if (key_data.len != 33) {
        mp_raise_msg(&mp_type_ValueError,
                    MP_ERROR_TEXT("key_data should be 33 bytes"));
    }

    if (args[2].u_obj != MP_OBJ_NULL) {
        mp_get_buffer_raise(args[2].u_obj, &chain_code_info, MP_BUFFER_READ);
        if (chain_code_info.len != 32) {
            mp_raise_msg(&mp_type_ValueError,
                        MP_ERROR_TEXT("chain_code should be 32 bytes"));
        }
    }

    if (args[3].u_obj != MP_OBJ_NULL) {
        if (!mp_obj_is_type(args[3].u_obj, &mod_foundation_ur_CryptoCoinInfo_type)) {
            mp_raise_msg(&mp_type_ValueError,
                        MP_ERROR_TEXT("use_info should be of type CryptoCoinInfo"));
        }

        use_info_obj = MP_OBJ_TO_PTR(args[3].u_obj);
    }

    if (args[4].u_obj != MP_OBJ_NULL) {
        if (!mp_obj_is_type(args[4].u_obj, &mod_foundation_ur_CryptoKeypath_type)) {
            mp_raise_msg(&mp_type_ValueError,
                        MP_ERROR_TEXT("origin should be of type CryptoKeypath"));
        }

        origin_obj = MP_OBJ_TO_PTR(args[4].u_obj);
    }

    ur_registry_new_derived_key(&value,
                                args[0].u_bool,
                                key_data.buf,
                                chain_code_info.buf,
                                &use_info_obj->info,
                                &origin_obj->keypath,
                                args[5].u_int);

    return MP_OBJ_FROM_PTR(mod_foundation_ur_Value_new(&value));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_foundation_ur_new_derived_key_obj,
                                  1,
                                  mod_foundation_ur_new_derived_key);

/// def new_crypto_psbt(data: bytes) -> Value:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_new_crypto_psbt(mp_obj_t data_in)
{
    mp_buffer_info_t data = {0};
    UR_Value value;

    mp_get_buffer_raise(data_in, &data, MP_BUFFER_READ);
    ur_registry_new_crypto_psbt(&value, data.buf, data.len);
    return MP_OBJ_FROM_PTR(mod_foundation_ur_Value_new(&value));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_new_crypto_psbt_obj,
                                 mod_foundation_ur_new_crypto_psbt);


/// def new_passport_response(data: bytes) -> Value:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_new_passport_response(size_t n_args,
                                                        const mp_obj_t *pos_args,
                                                        mp_map_t *kw_args)
{

    mp_buffer_info_t uuid = {0};
    UR_Solution solution = {0};
    UR_Value value = {0};

    static const mp_arg_t allowed_args[] = {
        { MP_QSTR_uuid,    MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_word1,   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_word2,   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_word3,   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_word4,   MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
        { MP_QSTR_model,   MP_ARG_KW_ONLY | MP_ARG_INT, {.u_int = 0} },
        { MP_QSTR_version, MP_ARG_KW_ONLY | MP_ARG_OBJ, {.u_obj = MP_OBJ_NULL} },
    };

    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)];
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args), allowed_args, args);

    mp_get_buffer_raise(args[0].u_obj, &uuid, MP_BUFFER_READ);
    if (uuid.len != 16) {
        mp_raise_msg(&mp_type_ValueError,
                    MP_ERROR_TEXT("uuid should be 33 bytes"));
    }

    GET_STR_DATA_LEN(args[1].u_obj, word1, word1_len);
    GET_STR_DATA_LEN(args[2].u_obj, word2, word2_len);
    GET_STR_DATA_LEN(args[3].u_obj, word3, word3_len);
    GET_STR_DATA_LEN(args[4].u_obj, word4, word4_len);

    solution.word1 = (const char *)word1;
    solution.word1_len = word1_len;
    solution.word2 = (const char *)word2;
    solution.word2_len = word2_len;
    solution.word3 = (const char *)word3;
    solution.word3_len = word3_len;
    solution.word4 = (const char *)word4;
    solution.word4_len = word4_len;

    GET_STR_DATA_LEN(args[6].u_obj, passport_firmware_version, passport_firmware_version_len);

    ur_registry_new_passport_response(&value,
                                      uuid.buf,
                                      &solution,
                                      args[5].u_int,
                                      (const char *)passport_firmware_version,
                                      passport_firmware_version_len);

    return MP_OBJ_FROM_PTR(mod_foundation_ur_Value_new(&value));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_foundation_ur_new_passport_response_obj,
                                  0,
                                  mod_foundation_ur_new_passport_response);

/// Encoder.

/// def encoder_start(value, max_fragment_len) -> None:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_encoder_start(mp_obj_t value_in,
                                                mp_obj_t max_fragment_len_in)
{
    mp_obj_Value_t *value = NULL;
    mp_int_t max_fragment_len = 0;

    if (!mp_obj_is_type(value_in, &mod_foundation_ur_Value_type)) {
        mp_raise_msg(&mp_type_ValueError, MP_ERROR_TEXT("invalid type for value"));
        return mp_const_none;
    }

    value = MP_OBJ_TO_PTR(value_in);
    max_fragment_len = mp_obj_get_int(max_fragment_len_in);
    ur_encoder_start(&UR_ENCODER, &value->value, max_fragment_len);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_ur_encoder_start_obj,
                                 mod_foundation_ur_encoder_start);

/// def encoder_next_part(ur_type, message, max_fragment_len) -> str:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_encoder_next_part(void)
{
    const char *ur;
    size_t ur_len;

    ur_encoder_next_part(&UR_ENCODER, &ur, &ur_len);

    vstr_t vstr;
    vstr_init(&vstr, ur_len + 1);
    vstr_add_strn(&vstr, ur, ur_len);

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_ur_encoder_next_part_obj,
                                 mod_foundation_ur_encoder_next_part);

/// Decoder.

/// def decoder_receive(ur_obj) -> None:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_decoder_receive(mp_obj_t ur_obj)
{
    UR_Error error = {0};

    mp_check_self(mp_obj_is_str(ur_obj));
    GET_STR_DATA_LEN(ur_obj, ur, ur_len);
    
    if (!ur_decoder_receive(&UR_DECODER, ur, ur_len, &error)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("%.*s"),
                          error.len, error.message);
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_decoder_receive_obj,
                                 mod_foundation_ur_decoder_receive);

/// def decoder_is_complete() -> bool:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_decoder_is_complete(void)
{
    return ur_decoder_is_complete(&UR_DECODER) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_ur_decoder_is_complete_obj,
                                 mod_foundation_ur_decoder_is_complete);

/// def decoder_estimated_percent_complete() -> int:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_decoder_estimated_percent_complete(void)
{
    return mp_obj_new_int(ur_decoder_estimated_percent_complete(&UR_DECODER));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_ur_decoder_estimated_percent_complete_obj,
                                 mod_foundation_ur_decoder_estimated_percent_complete);


/// def decoder_clear() -> None:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_decoder_clear(void)
{
    ur_decoder_clear(&UR_DECODER);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_ur_decoder_clear_obj, mod_foundation_ur_decoder_clear);

/// def decoder_decode_message() -> Value:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_decoder_decode_message(void)
{
    UR_Error error = {0};
    UR_Value value = {0};

    if (!ur_decoder_decode_message(&UR_DECODER, &value, &error)) {
        mp_raise_msg_varg(&mp_type_ValueError, MP_ERROR_TEXT("%.*s"),
                          error.len, error.message);
    }

    return MP_OBJ_FROM_PTR(mod_foundation_ur_Value_new(&value));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_ur_decoder_decode_message_obj,
                                 mod_foundation_ur_decoder_decode_message);

/// def validate(ur: str) -> bool:
///     """
///     """
STATIC mp_obj_t mod_foundation_ur_validate(mp_obj_t ur_obj)
{
    mp_check_self(mp_obj_is_str(ur_obj));
    GET_STR_DATA_LEN(ur_obj, ur, ur_len);

    return ur_validate(ur, ur_len) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_ur_validate_obj, mod_foundation_ur_validate);

STATIC const mp_rom_map_elem_t mod_foundation_ur_globals_table[] = {
    // Value.
    {MP_ROM_QSTR(MP_QSTR_NETWORK_MAINNET), MP_ROM_INT(UR_NETWORK_MAINNET)},
    {MP_ROM_QSTR(MP_QSTR_NETWORK_TESTNET), MP_ROM_INT(UR_NETWORK_TESTNET)},
    {MP_ROM_QSTR(MP_QSTR_PASSPORT_MODEL_FOUNDERS_EDITION), MP_ROM_INT(PASSPORT_MODEL_FOUNDERS_EDITION)},
    {MP_ROM_QSTR(MP_QSTR_PASSPORT_MODEL_BATCH2), MP_ROM_INT(PASSPORT_MODEL_BATCH2)},
    {MP_ROM_QSTR(MP_QSTR_Value), MP_ROM_PTR(&mod_foundation_ur_Value_type)},
    {MP_ROM_QSTR(MP_QSTR_CoinType), MP_ROM_PTR(&mod_foundation_ur_CoinType_type)},
    {MP_ROM_QSTR(MP_QSTR_CryptoCoinInfo), MP_ROM_PTR(&mod_foundation_ur_CryptoCoinInfo_type)},
    {MP_ROM_QSTR(MP_QSTR_CryptoKeypath), MP_ROM_PTR(&mod_foundation_ur_CryptoKeypath_type)},
    {MP_ROM_QSTR(MP_QSTR_PassportRequest), MP_ROM_PTR(&mod_foundation_ur_PassportRequest_type)},
    {MP_ROM_QSTR(MP_QSTR_new_bytes), MP_ROM_PTR(&mod_foundation_ur_new_bytes_obj)},
    {MP_ROM_QSTR(MP_QSTR_new_derived_key), MP_ROM_PTR(&mod_foundation_ur_new_derived_key_obj)},
    {MP_ROM_QSTR(MP_QSTR_new_crypto_psbt), MP_ROM_PTR(&mod_foundation_ur_new_crypto_psbt_obj)},
    {MP_ROM_QSTR(MP_QSTR_new_passport_response), MP_ROM_PTR(&mod_foundation_ur_new_passport_response_obj)},

    // Encoder.
    {MP_ROM_QSTR(MP_QSTR_encoder_start), MP_ROM_PTR(&mod_foundation_ur_encoder_start_obj)},
    {MP_ROM_QSTR(MP_QSTR_encoder_next_part), MP_ROM_PTR(&mod_foundation_ur_encoder_next_part_obj)},

    // Decoder.
    {MP_ROM_QSTR(MP_QSTR_decoder_receive), MP_ROM_PTR(&mod_foundation_ur_decoder_receive_obj)},
    {MP_ROM_QSTR(MP_QSTR_decoder_is_complete), MP_ROM_PTR(&mod_foundation_ur_decoder_is_complete_obj)},
    {MP_ROM_QSTR(MP_QSTR_decoder_estimated_percent_complete), MP_ROM_PTR(&mod_foundation_ur_decoder_estimated_percent_complete_obj)},
    {MP_ROM_QSTR(MP_QSTR_decoder_clear), MP_ROM_PTR(&mod_foundation_ur_decoder_clear_obj)},
    {MP_ROM_QSTR(MP_QSTR_decoder_decode_message), MP_ROM_PTR(&mod_foundation_ur_decoder_decode_message_obj)},
    {MP_ROM_QSTR(MP_QSTR_validate), MP_ROM_PTR(&mod_foundation_ur_validate_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_ur_globals, mod_foundation_ur_globals_table);

STATIC const mp_obj_module_t mod_foundation_ur_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_ur_globals,
};
