// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "py/objexcept.h"
#include "foundation.h"
#include <stdint.h>

STATIC const mp_obj_type_t mod_foundation_psbt_Xpriv_type;

/// class InvalidPSBTError(Exception):
///     """
///     """
STATIC MP_DEFINE_EXCEPTION(InvalidPSBTError, Exception);

/// class FraudulentPSBTError(Exception):
///     """
///     """
STATIC MP_DEFINE_EXCEPTION(FraudulentPSBTError, Exception);

/// class InternalPSBTError(Exception):
///     """
///     """
STATIC MP_DEFINE_EXCEPTION(InternalPSBTError, Exception);

static NORETURN void mod_foundation_psbt_raise_validation(ValidationResult *result)
{
    switch (result->tag) {
        case VALIDATION_RESULT_OK:
            mp_raise_msg(&mp_type_InternalPSBTError,
                         MP_ERROR_TEXT("Tried to raise exception from OK value"));
            break;
        case VALIDATION_RESULT_INTERNAL_ERROR:
            mp_raise_msg(&mp_type_InternalPSBTError,
                         MP_ERROR_TEXT("Internal validation error"));
            break;
        case VALIDATION_RESULT_INVALID_XPRIV:
            mp_raise_msg(&mp_type_InternalPSBTError,
                         MP_ERROR_TEXT("The xpriv passed is invalid"));
            break;
        case VALIDATION_RESULT_PARSER_ERROR:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Failed to parse PSBT"));
            break;
        case VALIDATION_RESULT_INVALID_WITNESS_SCRIPT:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Invalid witness script"));
            break;
        case VALIDATION_RESULT_INVALID_REDEEM_SCRIPT:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Invalid redeem script"));
            break;
        case VALIDATION_RESULT_UNSUPPORTED_SIGHASH:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Unsupported SIGHASH"));
            break;
        case VALIDATION_RESULT_TXID_MISMATCH:
            mp_raise_msg(&mp_type_FraudulentPSBTError,
                         MP_ERROR_TEXT("Previous transaction ID does not match calculated one"));
            break;
        case VALIDATION_RESULT_MISSING_PREVIOUS_TXID:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Previous transaction ID missing"));
            break;
        case VALIDATION_RESULT_MISSING_REDEEM_WITNESS_SCRIPT:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Input is missing redeem script"));
            break;
        case VALIDATION_RESULT_TAPROOT_OUTPUT_INVALID_PUBLIC_KEY:
            mp_raise_msg(&mp_type_FraudulentPSBTError,
                         MP_ERROR_TEXT("Taproot output public key is invalid"));
            break;
        case VALIDATION_RESULT_TOO_MANY_INPUTS:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Transaction has too many inputs for Passport to handle"));
            break;
        case VALIDATION_RESULT_TOO_MANY_OUTPUTS:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Transaction has too many outputs for Passport to handle"));
            break;
        case VALIDATION_RESULT_TOO_MANY_OUTPUT_KEYS:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Output has too many keys for Passport to handle"));
            break;
        case VALIDATION_RESULT_MULTIPLE_KEYS_NOT_EXPECTED:
            mp_raise_msg(&mp_type_FraudulentPSBTError,
                         MP_ERROR_TEXT("Multiple keys not expected"));
            break;
        case VALIDATION_RESULT_FRAUDULENT_OUTPUT_PUBLIC_KEY:
            mp_raise_msg(&mp_type_FraudulentPSBTError,
                         MP_ERROR_TEXT("Fraudulent output public key"));
            break;
        case VALIDATION_RESULT_MISSING_OUTPUT:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Missing output"));
            break;
        case VALIDATION_RESULT_UNKNOWN_OUTPUT_SCRIPT:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("Unsupported output script"));
            break;
        case VALIDATION_RESULT_FRAUDULENT_WITNESS_UTXO:
            mp_raise_msg(&mp_type_InvalidPSBTError,
                         MP_ERROR_TEXT("The witness UTXO of an input is fraudulent"));
            break;
        default:
            mp_raise_msg(&mp_type_InternalPSBTError,
                         MP_ERROR_TEXT("Unhandled case in validation result"));
            break;
    }
}

/// class Value:
///     """
///     """
typedef struct _mp_obj_Xpriv_t {
    mp_obj_base_t base;
    Xpriv xpriv;
} mp_obj_Xpriv_t;

/// def __init__(self) -> None:
///     """
///     """
STATIC mp_obj_t mod_foundation_psbt_Xpriv_make_new(const mp_obj_type_t *type,
                                                   size_t n_args, size_t n_kw,
                                                   const mp_obj_t *args) {
    STATIC const mp_arg_t allowed_args[] = {
        {MP_QSTR_chain_code,
         MP_ARG_REQUIRED | MP_ARG_KW_ONLY | MP_ARG_OBJ,
         {.u_obj = mp_const_empty_bytes}},
        {MP_QSTR_private_key,
         MP_ARG_KW_ONLY | MP_ARG_OBJ,
         {.u_obj = mp_const_empty_bytes}},
    };
    mp_arg_val_t vals[MP_ARRAY_SIZE(allowed_args)] = {0};
    mp_arg_parse_all_kw_array(n_args, n_kw, args, MP_ARRAY_SIZE(allowed_args),
                              allowed_args, vals);

    mp_buffer_info_t chain_code = {0};
    mp_buffer_info_t private_key = {0};
    mp_get_buffer_raise(vals[0].u_obj, &chain_code, MP_BUFFER_READ);
    mp_get_buffer_raise(vals[1].u_obj, &private_key, MP_BUFFER_READ);

    if (chain_code.len != 32) {
        mp_raise_ValueError(MP_ERROR_TEXT("chain_code is invalid"));
    }

    if (private_key.len != 32) {
        mp_raise_ValueError(MP_ERROR_TEXT("private_key is invalid"));
    }

    mp_obj_Xpriv_t *o = m_new_obj(mp_obj_Xpriv_t);
    o->base.type = &mod_foundation_psbt_Xpriv_type;

    // For this module we assume that the user should
    // pass master private keys for PSBT validation.
    //
    // This can be extended in the future to support
    // child nodes by adding the respective parameters.
    o->xpriv.depth = 0;
    o->xpriv.child_number = 0;
    memset(o->xpriv.parent_fingerprint, 0, 4);
    memcpy(o->xpriv.chain_code, chain_code.buf, 32);
    memcpy(o->xpriv.private_key, private_key.buf, 32);

    return MP_OBJ_FROM_PTR(o);
}

STATIC const mp_rom_map_elem_t mod_foundation_psbt_Xpriv_locals_dict_table[] = {
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_psbt_Xpriv_locals_dict, mod_foundation_psbt_Xpriv_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_psbt_Xpriv_type = {
    { &mp_type_type },
    .name = MP_QSTR_Xpriv,
    .make_new = mod_foundation_psbt_Xpriv_make_new,
    .locals_dict = (mp_obj_dict_t *)&mod_foundation_psbt_Xpriv_locals_dict,
};

/// class TransactionDetails:
///     """
///     """
typedef struct _mp_obj_TransactionDetails_t {
    mp_obj_base_t base;
    uint64_t total_with_change;
    uint64_t total_change;
    uint64_t fee;
    bool is_self_send;
} mp_obj_TransactionDetails_t;

/// def total_with_change(self) -> int:
///     """
///     """
STATIC mp_obj_t mod_foundation_psbt_TransactionDetails_total_with_change(mp_obj_t self_in) {
    mp_obj_TransactionDetails_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_int_from_ull(self->total_with_change);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_psbt_TransactionDetails_total_with_change_obj,
                                 mod_foundation_psbt_TransactionDetails_total_with_change);

/// def total_change(self) -> int:
///     """
///     """
STATIC mp_obj_t mod_foundation_psbt_TransactionDetails_total_change(mp_obj_t self_in) {
    mp_obj_TransactionDetails_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_int_from_ull(self->total_change);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_psbt_TransactionDetails_total_change_obj,
                                 mod_foundation_psbt_TransactionDetails_total_change);

/// def fee(self) -> int:
///     """
///     """
STATIC mp_obj_t mod_foundation_psbt_TransactionDetails_fee(mp_obj_t self_in) {
    mp_obj_TransactionDetails_t *self = MP_OBJ_TO_PTR(self_in);

    return mp_obj_new_int_from_ull(self->fee);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_psbt_TransactionDetails_fee_obj,
                                 mod_foundation_psbt_TransactionDetails_fee);

/// def is_self_send(self) -> boolean:
///     """
///     """
STATIC mp_obj_t mod_foundation_psbt_TransactionDetails_is_self_send(mp_obj_t self_in) {
    mp_obj_TransactionDetails_t *self = MP_OBJ_TO_PTR(self_in);

    return self->is_self_send ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_psbt_TransactionDetails_is_self_send_obj,
                                 mod_foundation_psbt_TransactionDetails_is_self_send);

STATIC const mp_rom_map_elem_t mod_foundation_psbt_TransactionDetails_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_total_with_change),
      MP_ROM_PTR(&mod_foundation_psbt_TransactionDetails_total_with_change_obj) },
    { MP_ROM_QSTR(MP_QSTR_total_change),
      MP_ROM_PTR(&mod_foundation_psbt_TransactionDetails_total_change_obj) },
    { MP_ROM_QSTR(MP_QSTR_is_self_send),
      MP_ROM_PTR(&mod_foundation_psbt_TransactionDetails_is_self_send_obj) },
    { MP_ROM_QSTR(MP_QSTR_fee),
      MP_ROM_PTR(&mod_foundation_psbt_TransactionDetails_fee_obj) },
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_psbt_TransactionDetails_locals_dict,
                            mod_foundation_psbt_TransactionDetails_locals_dict_table);

STATIC const mp_obj_type_t mod_foundation_psbt_TransactionDetails_type = {
    { &mp_type_type },
    .name = MP_QSTR_TransactionDetails,
    .locals_dict = (mp_obj_dict_t *)&mod_foundation_psbt_TransactionDetails_locals_dict,
};

STATIC bool mod_foundation_psbt_validate_event(void *data, const ValidationEvent *e)
{
    mp_obj_t handle_event = MP_OBJ_FROM_PTR(data);
    mp_obj_t tuple[2];
    bool refresh_ui = false;

    if (handle_event == mp_const_none) {
        return refresh_ui;
    }

    switch (e->tag) {
        case VALIDATION_EVENT_PROGRESS:
            refresh_ui = true;
            mp_call_function_2(handle_event,
                               MP_OBJ_NEW_QSTR(MP_QSTR_progress),
                               mp_obj_new_int(e->progress));
            break;
        case VALIDATION_EVENT_OUTPUT_ADDRESS:
            refresh_ui = true;
            tuple[0] = mp_obj_new_str_copy(&mp_type_str,
                                           (const uint8_t*)e->OUTPUT_ADDRESS.address,
                                           strlen((const char*)e->OUTPUT_ADDRESS.address));
            tuple[1] = mp_obj_new_int(e->OUTPUT_ADDRESS.amount);
            mp_call_function_2(handle_event, MP_OBJ_NEW_QSTR(MP_QSTR_output_address),
                               mp_obj_new_tuple(2, tuple));
            break;
        case VALIDATION_EVENT_CHANGE_ADDRESS:
            refresh_ui = true;
            tuple[0] = mp_obj_new_str_copy(&mp_type_str,
                                           (const uint8_t*)e->CHANGE_ADDRESS.address,
                                           strlen((const char*)e->CHANGE_ADDRESS.address));
            tuple[1] = mp_obj_new_int(e->CHANGE_ADDRESS.amount);
            mp_call_function_2(handle_event, MP_OBJ_NEW_QSTR(MP_QSTR_change_address),
                               mp_obj_new_tuple(2, tuple));
        default:
            break;
    }

    return refresh_ui;
}

STATIC mp_obj_t mod_foundation_psbt_validate(size_t n_args, const mp_obj_t *pos_args, mp_map_t *kw_args)
{
    STATIC const mp_arg_t allowed_args[] = {
        {MP_QSTR_offset, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0}},
        {MP_QSTR_len, MP_ARG_REQUIRED | MP_ARG_INT, {.u_int = 0}},
        {MP_QSTR_is_testnet, MP_ARG_REQUIRED | MP_ARG_BOOL, {.u_bool = false}},
        {MP_QSTR_xpriv, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
        {MP_QSTR_handle_event, MP_ARG_REQUIRED | MP_ARG_OBJ, {.u_rom_obj = MP_ROM_NONE}},
    };
    mp_arg_val_t args[MP_ARRAY_SIZE(allowed_args)] = {0};
    mp_arg_parse_all(n_args, pos_args, kw_args, MP_ARRAY_SIZE(allowed_args),
                     allowed_args, args);

    Network network = args[2].u_bool ? NETWORK_TESTNET : NETWORK_MAINNET;

    if (!mp_obj_is_type(args[3].u_obj, &mod_foundation_psbt_Xpriv_type)) {
        mp_raise_msg(&mp_type_ValueError,
                    MP_ERROR_TEXT("xpriv should be of Xpriv type"));
    }
    mp_obj_Xpriv_t *xpriv = MP_OBJ_TO_PTR(args[3].u_obj);

    ValidationResult result = {0};
    if (!foundation_psbt_validate(args[0].u_int, args[1].u_int,
                                  network, &xpriv->xpriv,
                                  MP_OBJ_TO_PTR(args[4].u_obj),
                                  mod_foundation_psbt_validate_event,
                                  &result)) {
        mod_foundation_psbt_raise_validation(&result);
    }

    if (result.tag != VALIDATION_RESULT_OK) {
        mp_raise_msg(&mp_type_InternalPSBTError,
                     MP_ERROR_TEXT("Validation result tag should be OK"));
    }

    mp_obj_TransactionDetails_t *o = m_new_obj(mp_obj_TransactionDetails_t);
    o->base.type = &mod_foundation_psbt_TransactionDetails_type;
    o->total_with_change = result.OK.total_with_change;
    o->total_change = result.OK.total_change;
    o->fee = result.OK.fee;
    o->is_self_send = result.OK.is_self_send;

    return MP_OBJ_FROM_PTR(o);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_KW(mod_foundation_psbt_validate_obj, 4, mod_foundation_psbt_validate);

STATIC const mp_rom_map_elem_t mod_foundation_psbt_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_InvalidPSBTError), MP_ROM_PTR(&mp_type_InvalidPSBTError)},
    {MP_ROM_QSTR(MP_QSTR_FraudulentPSBTError), MP_ROM_PTR(&mp_type_FraudulentPSBTError)},
    {MP_ROM_QSTR(MP_QSTR_InternalPSBTError), MP_ROM_PTR(&mp_type_InternalPSBTError)},
    {MP_ROM_QSTR(MP_QSTR_Xpriv), MP_ROM_PTR(&mod_foundation_psbt_Xpriv_type)},
    {MP_ROM_QSTR(MP_QSTR_TransactionDetails), MP_ROM_PTR(&mod_foundation_psbt_TransactionDetails_type)},
    {MP_ROM_QSTR(MP_QSTR_validate), MP_ROM_PTR(&mod_foundation_psbt_validate_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_psbt_globals, mod_foundation_psbt_globals_table);

STATIC const mp_obj_module_t mod_foundation_psbt_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_psbt_globals,
};
