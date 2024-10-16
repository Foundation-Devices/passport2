// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Passport hardware build only. It is not shared
// with the unix simulator.

// Include all submodules and classes implementations.
#include "modpassport-backlight.h"
#include "modpassport-camera.h"
#include "modpassport-fuelgauge.h"
#include "modpassport-mem.h"
#include "modpassport-noise.h"
#include "modpassport-powermon.h"
#include "modpassport-settingsflash.h"
#include "modpassport-system.h"

#include "uECC.h"
#include "se-config.h"
#include "se.h"

/// package: passport

STATIC MP_DEFINE_EXCEPTION(InvalidFirmwareUpdate, Exception);

/// def supply_chain_challenge(self, challenge: bytearray, response: bytearray) -> boolean:
///     """
///     Perform the supply chain challenge (HMAC)
///     """
STATIC mp_obj_t mod_passport_supply_chain_challenge(mp_obj_t challenge_obj, mp_obj_t response_obj) {
    mp_buffer_info_t challenge_info = {0};
    mp_buffer_info_t response_info  = {0};

    mp_get_buffer_raise(challenge_obj, &challenge_info, MP_BUFFER_READ);
    mp_get_buffer_raise(response_obj, &response_info, MP_BUFFER_WRITE);

    se_pair_unlock();
    int rc = se_hmac32(KEYNUM_supply_chain, challenge_info.buf, response_info.buf);
    if (rc == 0) {
        return mp_const_true;
    }

    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_supply_chain_challenge_obj, mod_passport_supply_chain_challenge);

/// def verify_supply_chain_server_signature(self, hash: bytearray, signature: bytearray) -> boolean:
///     """
///     Verify server signature.
///     """
STATIC mp_obj_t mod_passport_verify_supply_chain_server_signature(mp_obj_t hash_obj, mp_obj_t signature_obj) {
    mp_buffer_info_t hash_info      = {0};
    mp_buffer_info_t signature_info = {0};
    int              rc             = 0;

    mp_get_buffer_raise(hash_obj, &hash_info, MP_BUFFER_READ);
    mp_get_buffer_raise(signature_obj, &signature_info, MP_BUFFER_READ);

    rc = uECC_verify(supply_chain_validation_server_pubkey, hash_info.buf, hash_info.len, signature_info.buf,
                     uECC_secp256k1());
    return rc == 0 ? mp_const_false : mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_verify_supply_chain_server_signature_obj,
                                 mod_passport_verify_supply_chain_server_signature);

/// def verify_update_header(self, header: bytearray) -> None:
///     '''
///     Verify the given firmware header bytes as a potential candidate to be
///     installed.
///     '''
STATIC mp_obj_t mod_passport_verify_update_header(mp_obj_t header) {
    mp_obj_t tuple[2];

    mp_buffer_info_t header_info;
    mp_get_buffer_raise(header, &header_info, MP_BUFFER_READ);

    // Build the current board hash so we can get the minimum firmware
    // timestamp
    uint8_t current_board_hash[HASH_LEN] = {0};
    get_current_board_hash(current_board_hash);

    uint32_t firmware_timestamp = se_get_firmware_timestamp(current_board_hash);

    FirmwareResult result = {0};
    foundation_firmware_verify_update_header(header_info.buf,
                                             header_info.len,
                                             firmware_timestamp,
                                             &result);

    switch (result.tag) {
        case FIRMWARE_RESULT_HEADER_OK:
            tuple[0] = mp_obj_new_str_copy(&mp_type_str,
                                           (const uint8_t*)result.HEADER_OK.version,
                                           strlen((const char*)result.HEADER_OK.version));
            tuple[1] = result.HEADER_OK.signed_by_user ? mp_const_true : mp_const_false;
            return mp_obj_new_tuple(2, tuple);
        case FIRMWARE_RESULT_INVALID_HEADER:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Invalid firmware header"));
        case FIRMWARE_RESULT_UNKNOWN_MAGIC:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Unknown firmware magic bytes"));
            break;
        case FIRMWARE_RESULT_INVALID_TIMESTAMP:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Invalid firmware timestamp"));
            break;
        case FIRMWARE_RESULT_TOO_SMALL:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware size is too small: %"PRIu32" bytes."),
                              result.TOO_SMALL.len);
            break;
        case FIRMWARE_RESULT_TOO_BIG:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware size is too big: %"PRIu32" bytes."),
                              result.TOO_BIG.len);
            break;
        case FIRMWARE_RESULT_TOO_OLD:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware is older than current, timestamp is: %"PRIu32"."),
                              result.TOO_OLD.timestamp);
            break;
        case FIRMWARE_RESULT_INVALID_PUBLIC_KEY1_INDEX:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Public Key is out of range (%"PRIu32")."),
                              result.INVALID_PUBLIC_KEY1_INDEX.index);
            break;
        case FIRMWARE_RESULT_INVALID_PUBLIC_KEY2_INDEX:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Public Key is out of range (%"PRIu32")."),
                              result.INVALID_PUBLIC_KEY2_INDEX.index);
            break;
        case FIRMWARE_RESULT_SAME_PUBLIC_KEY:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Same Public Key was used for both signatures (%"PRIu32")."),
                              result.SAME_PUBLIC_KEY.index);
            break;
        case FIRMWARE_RESULT_MISSING_USER_PUBLIC_KEY:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Missing user public key"));
            break;
        default:
            break;
    }

    mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                 MP_ERROR_TEXT("Unhandled case in firmware verification"));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_verify_update_header_obj,
                                 mod_passport_verify_update_header);

STATIC mp_obj_t mod_passport_verify_update_signatures(mp_obj_t header, mp_obj_t validation_hash) {
    uint8_t buf[72];
    uint8_t public_key[64];

    mp_buffer_info_t header_info;
    mp_get_buffer_raise(header, &header_info, MP_BUFFER_READ);

    mp_buffer_info_t validation_hash_info;
    mp_get_buffer_raise(validation_hash, &validation_hash_info, MP_BUFFER_READ);

    // Build the current board hash so we can get the minimum firmware
    // timestamp
    uint8_t current_board_hash[HASH_LEN] = {0};
    get_current_board_hash(current_board_hash);

    uint32_t firmware_timestamp = se_get_firmware_timestamp(current_board_hash);

    se_pair_unlock();
    bool has_user_key = se_read_data_slot(KEYNUM_user_fw_pubkey, buf, sizeof(buf)) == 0;
    memcpy(public_key, buf, sizeof(public_key));

    FirmwareResult result = {0};
    foundation_firmware_verify_update_signatures(header_info.buf,
                                                 header_info.len,
                                                 firmware_timestamp,
                                                 validation_hash_info.buf,
                                                 has_user_key ? &public_key : NULL,
                                                 &result);

    // Signature verification also validates the header again, so, we have
    // to handle the errors again.
    //
    // TODO: This should be factored out.
    switch (result.tag) {
        case FIRMWARE_RESULT_SIGNATURES_OK:
            return mp_const_true;
        case FIRMWARE_RESULT_INVALID_HEADER:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Invalid firmware header"));
        case FIRMWARE_RESULT_UNKNOWN_MAGIC:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Unknown firmware magic bytes"));
            break;
        case FIRMWARE_RESULT_INVALID_TIMESTAMP:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Invalid firmware timestamp"));
            break;
        case FIRMWARE_RESULT_TOO_SMALL:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware size is too small: %"PRIu32" bytes."),
                              result.TOO_SMALL.len);
            break;
        case FIRMWARE_RESULT_TOO_BIG:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware size is too big: %"PRIu32" bytes."),
                              result.TOO_BIG.len);
            break;
        case FIRMWARE_RESULT_TOO_OLD:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Firmware is older than current, timestamp is: %"PRIu32"."),
                              result.TOO_OLD.timestamp);
            break;
        case FIRMWARE_RESULT_INVALID_PUBLIC_KEY1_INDEX:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Public Key 1 is out of range (%"PRIu32")."),
                              result.INVALID_PUBLIC_KEY1_INDEX.index);
            break;
        case FIRMWARE_RESULT_INVALID_PUBLIC_KEY2_INDEX:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Public Key 2 is out of range (%"PRIu32")."),
                              result.INVALID_PUBLIC_KEY2_INDEX.index);
            break;
        case FIRMWARE_RESULT_SAME_PUBLIC_KEY:
            mp_raise_msg_varg(&mp_type_InvalidFirmwareUpdate,
                              MP_ERROR_TEXT("Same Public Key was used for both signatures (%"PRIu32")."),
                              result.SAME_PUBLIC_KEY.index);
            break;
        case FIRMWARE_RESULT_INVALID_USER_SIGNATURE:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("User signature verification failed"));
            break;
        case FIRMWARE_RESULT_FAILED_SIGNATURE1:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("First signature verification failed"));
        case FIRMWARE_RESULT_FAILED_SIGNATURE2:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Second signature verification failed"));
            break;
        case FIRMWARE_RESULT_MISSING_USER_PUBLIC_KEY:
            mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                         MP_ERROR_TEXT("Missing user public key"));
            break;
        default:
            break;
    }

    mp_raise_msg(&mp_type_InvalidFirmwareUpdate,
                 MP_ERROR_TEXT("Unhandled case in firmware signatures verification"));
    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_verify_update_signatures_obj,
                                 mod_passport_verify_update_signatures);

STATIC const mp_rom_map_elem_t passport_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_passport)},
    {MP_ROM_QSTR(MP_QSTR_InvalidFirmwareUpdate), MP_ROM_PTR(&mp_type_InvalidFirmwareUpdate)},
    {MP_ROM_QSTR(MP_QSTR_camera), MP_ROM_PTR(&mod_passport_camera_module)},
    {MP_ROM_QSTR(MP_QSTR_IS_SIMULATOR), MP_ROM_FALSE},
    {MP_ROM_QSTR(MP_QSTR_supply_chain_challenge), MP_ROM_PTR(&mod_passport_supply_chain_challenge_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify_supply_chain_server_signature),
     MP_ROM_PTR(&mod_passport_verify_supply_chain_server_signature_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify_update_header),
     MP_ROM_PTR(&mod_passport_verify_update_header_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify_update_signatures),
     MP_ROM_PTR(&mod_passport_verify_update_signatures_obj)},
#ifdef SCREEN_MODE_COLOR
    {MP_ROM_QSTR(MP_QSTR_IS_COLOR), MP_ROM_TRUE},
#else
    {MP_ROM_QSTR(MP_QSTR_IS_COLOR), MP_ROM_FALSE},
#endif  // SCREEN_MODE_COLOR
#ifdef DEV_BUILD
    {MP_ROM_QSTR(MP_QSTR_IS_DEV), MP_ROM_TRUE},
#else
    {MP_ROM_QSTR(MP_QSTR_IS_DEV), MP_ROM_FALSE},
#endif
#ifdef HAS_FUEL_GAUGE
    {MP_ROM_QSTR(MP_QSTR_HAS_FUEL_GAUGE), MP_ROM_TRUE},
#else
    {MP_ROM_QSTR(MP_QSTR_HAS_FUEL_GAUGE), MP_ROM_FALSE},
#endif  // HAS_FUEL_GAUGE
#ifdef HAS_FUEL_GAUGE
    {MP_ROM_QSTR(MP_QSTR_fuelgauge), MP_ROM_PTR(&mod_passport_fuelgauge_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_Backlight), MP_ROM_PTR(&mod_passport_Backlight_type)},
    {MP_ROM_QSTR(MP_QSTR_Noise), MP_ROM_PTR(&mod_passport_Noise_type)},
#ifdef SCREEN_MODE_MONO
    {MP_ROM_QSTR(MP_QSTR_Powermon), MP_ROM_PTR(&mod_passport_Powermon_type)},
    {MP_ROM_QSTR(MP_QSTR_SettingsFlash), MP_ROM_PTR(&mod_passport_SettingsFlash_type)},
#endif
    {MP_ROM_QSTR(MP_QSTR_mem), MP_ROM_PTR(&mod_passport_mem_module)},
    {MP_ROM_QSTR(MP_QSTR_System), MP_ROM_PTR(&mod_passport_System_type)}};
STATIC MP_DEFINE_CONST_DICT(passport_module_globals, passport_module_globals_table);

/* Define module object. */
const mp_obj_module_t passport_user_cmodule = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&passport_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_passport, passport_user_cmodule, PASSPORT_FOUNDATION_ENABLED);
