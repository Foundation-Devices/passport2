// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later
//
// This code is specific to the Passport hardware build only. It is not shared
// with the unix simulator.

// Include all submodules and classes implementations.
#include "modpassport-backlight.h"
#include "modpassport-boardrev.h"
#include "modpassport-camera.h"
#include "modpassport-fuelgauge.h"
#include "modpassport-noise.h"
#include "modpassport-powermon.h"
#include "modpassport-settingsflash.h"
#include "modpassport-sram4.h"
#include "modpassport-system.h"

#include "uECC.h"
#include "se-config.h"
#include "se.h"

/// package: passport

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

STATIC const mp_rom_map_elem_t passport_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_passport)},
    {MP_ROM_QSTR(MP_QSTR_camera), MP_ROM_PTR(&mod_passport_camera_module)},
    {MP_ROM_QSTR(MP_QSTR_IS_SIMULATOR), MP_ROM_FALSE},
    {MP_ROM_QSTR(MP_QSTR_supply_chain_challenge), MP_ROM_PTR(&mod_passport_supply_chain_challenge_obj)},
    {MP_ROM_QSTR(MP_QSTR_verify_supply_chain_server_signature),
     MP_ROM_PTR(&mod_passport_verify_supply_chain_server_signature_obj)},
#ifdef SCREEN_MODE_COLOR
    {MP_ROM_QSTR(MP_QSTR_IS_COLOR), MP_ROM_TRUE},
#else
    {MP_ROM_QSTR(MP_QSTR_IS_COLOR), MP_ROM_FALSE},
#endif  // SCREEN_MODE_COLOR
#ifdef HAS_FUEL_GAUGE
    {MP_ROM_QSTR(MP_QSTR_HAS_FUEL_GAUGE), MP_ROM_TRUE},
#else
    {MP_ROM_QSTR(MP_QSTR_HAS_FUEL_GAUGE), MP_ROM_FALSE},
#endif  // HAS_FUEL_GAUGE
#ifdef HAS_FUEL_GAUGE
    {MP_ROM_QSTR(MP_QSTR_fuelgauge), MP_ROM_PTR(&mod_passport_fuelgauge_module)},
#endif
    {MP_ROM_QSTR(MP_QSTR_Backlight), MP_ROM_PTR(&mod_passport_Backlight_type)},
    {MP_ROM_QSTR(MP_QSTR_Boardrev), MP_ROM_PTR(&mod_passport_Boardrev_type)},
    {MP_ROM_QSTR(MP_QSTR_Noise), MP_ROM_PTR(&mod_passport_Noise_type)},
#ifdef SCREEN_MODE_MONO
    {MP_ROM_QSTR(MP_QSTR_Powermon), MP_ROM_PTR(&mod_passport_Powermon_type)},
    {MP_ROM_QSTR(MP_QSTR_SettingsFlash), MP_ROM_PTR(&mod_passport_SettingsFlash_type)},
#endif
    {MP_ROM_QSTR(MP_QSTR_sram4), MP_ROM_PTR(&mod_passport_sram4_module)},
    {MP_ROM_QSTR(MP_QSTR_System), MP_ROM_PTR(&mod_passport_System_type)}};
STATIC MP_DEFINE_CONST_DICT(passport_module_globals, passport_module_globals_table);

/* Define module object. */
const mp_obj_module_t passport_user_cmodule = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&passport_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_passport, passport_user_cmodule, PASSPORT_FOUNDATION_ENABLED);
