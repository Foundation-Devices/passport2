// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/mphal.h"
#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"

#include "uECC.h"
#include "eeprom.h"
#include "se-config.h"
#include "se.h"
#include "fwheader.h"
#include "sha256.h"
#include "pins.h"
#include "hash.h"
#include "gpio.h"
#include "display.h"
#include "firmware-keys.h"
#include "frequency.h"
#include "dispatch.h"
#include "adc.h"
#include "utils.h"

#define SYSTEM_DEBUG 0
#define SECRETS_FLASH_START (0x81C0000)
#define SECRETS_FLASH_SIZE (0x20000)

#define SHA256_BLOCK_LENGTH (64)
#define SHA256_DIGEST_LENGTH (32)

#define MAX_SERIAL_NUMBER_LEN (20)

STATIC uint8_t supply_chain_validation_server_pubkey[64] = {
    0x75, 0xF6, 0xCD, 0xDB, 0x93, 0x49, 0x59, 0x9D, 0x4B, 0xB2, 0xDF, 0x82, 0xBC, 0xF9, 0x8E, 0x85,
    0x45, 0x6C, 0xFB, 0xE2, 0x87, 0x57, 0xFF, 0x77, 0x5D, 0xB0, 0x4C, 0xAE, 0x70, 0x1B, 0xDC, 0x00,
    0x53, 0x4E, 0x0C, 0x70, 0x01, 0x90, 0x6C, 0x6F, 0xFB, 0xA6, 0x15, 0xAF, 0xDB, 0x67, 0xDE, 0xF9,
    0x46, 0x96, 0x4B, 0xB4, 0x39, 0xD0, 0x02, 0x3E, 0xF6, 0x59, 0xF5, 0x80, 0xBB, 0x31, 0x11, 0x3E};

STATIC void _hmac_sha256(uint8_t* key, uint32_t key_len, uint8_t* msg, uint32_t msg_len, uint8_t* hmac);

/// package: passport

/// class System:
///     """
///     """
typedef struct _mp_obj_System_t {
    mp_obj_base_t base;
} mp_obj_System_t;

/// def __init__(self, mode: int, key: bytes, iv: bytes = None) -> boolean:
///     """
///     Initialize System context.
///     """
STATIC mp_obj_t mod_passport_System_make_new(const mp_obj_type_t* type,
                                             size_t               n_args,
                                             size_t               n_kw,
                                             const mp_obj_t*      args) {
    mp_obj_System_t* o = m_new_obj(mp_obj_System_t);
    o->base.type       = type;
    eeprom_init(&g_hi2c2);
    return MP_OBJ_FROM_PTR(o);
}

/// def reset(self) -> None:
///     """
///     Perform a warm reset of the system (should be mostly the same as turning it off and then on).
///     """
STATIC mp_obj_t mod_passport_System_reset(mp_obj_t self) {
    passport_reset();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_reset_obj, mod_passport_System_reset);

/// def shutdown(self) -> None:
///     """
///     Shutdown power to the Passport.
///     """
STATIC mp_obj_t mod_passport_System_shutdown(mp_obj_t self) {
    // We clear the memory display and then shutdown
    display_clean_shutdown();
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_shutdown_obj, mod_passport_System_shutdown);

/// def dispatch(self, command: int, buf: bytes, len: int, arg2: int, ) -> array of strings:
///     """
///     Dispatch system function by command number. This is a carry-over from the old firewall
///     code. We can probably switch this to direct function calls instead. The only benefit is
///     that this gives us a nice single point to handle RDP level 2 checks and other security checks.
///     """
STATIC mp_obj_t mod_passport_System_dispatch(size_t n_args, const mp_obj_t* args) {
    int8_t   command = mp_obj_get_int(args[1]);
    uint16_t arg2    = mp_obj_get_int(args[3]);
    int      result;

    frequency_turbo(true);

    if (args[2] == mp_const_none) {
        result = se_dispatch(command, NULL, 0, arg2, 0, 0);
    } else {
        mp_buffer_info_t buf_info;  // Use MP_BUFFER_WRITE below so any updates are copied back up
        mp_get_buffer_raise(args[2], &buf_info, MP_BUFFER_WRITE);

        result = se_dispatch(command, buf_info.buf, buf_info.len, arg2, 0, 0);
    }

    frequency_turbo(false);

    return mp_obj_new_int(result);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_passport_System_dispatch_obj, 4, 4, mod_passport_System_dispatch);

/// def get_software_info(self) -> (str, int, int, bool):
///     """
///     Get version, timestamp & hash of the firmware and bootloader as a tuple.
///     """
STATIC mp_obj_t mod_passport_System_get_software_info(mp_obj_t self) {
    passport_firmware_header_t* fwhdr        = (passport_firmware_header_t*)FW_HDR;
    mp_obj_t                    tuple[5]     = {0};
    uint32_t                    boot_counter = 0;

    // Firmware version
    tuple[0] = mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)fwhdr->info.fwversion,
                                   strlen((const char*)fwhdr->info.fwversion));

    // Firmware timestamp
    tuple[1] = mp_obj_new_int_from_uint(fwhdr->info.timestamp);

    se_get_counter(&boot_counter, 1);
    tuple[2] = mp_obj_new_int_from_uint(boot_counter);

    // User-signed firmware?
    tuple[3] = (fwhdr->signature.pubkey1 == FW_USER_KEY) ? mp_const_true : mp_const_false;

    // Firmware date string
    tuple[4] =
        mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)fwhdr->info.fwdate, strlen((const char*)fwhdr->info.fwdate));

    return mp_obj_new_tuple(5, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_get_software_info_obj, mod_passport_System_get_software_info);

/// def progress_bar(self, progress: int) -> None:
///     """
///     Draw a progress bar to the specified amount (0-1.0)
///     """
STATIC mp_obj_t mod_passport_System_progress_bar(mp_obj_t self, mp_obj_t _progress) {
    // int8_t progress = mp_obj_get_int(_progress);
    // display_progress_bar(PROGRESS_BAR_MARGIN, PROGRESS_BAR_Y, SCREEN_WIDTH - (PROGRESS_BAR_MARGIN * 2),
    //                      PROGRESS_BAR_HEIGHT, progress);
    //
    // // Showing just the lines that changed is much faster and avoids full-screen flicker
    // display_show_lines(PROGRESS_BAR_Y, PROGRESS_BAR_Y + PROGRESS_BAR_HEIGHT);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_progress_bar_obj, mod_passport_System_progress_bar);

/// def turbo(self, enable: bool) -> None
///     """
///     Enable or disable turbo mode (fastest MCU frequency)
///     """
STATIC mp_obj_t mod_passport_System_turbo(mp_obj_t self, mp_obj_t enable_obj) {
    frequency_turbo(mp_obj_is_true(enable_obj));
    // printf("%s: %lu, %lu, %lu, %lu, %lu\n", enable ? "enable" : "disabled", HAL_RCC_GetSysClockFreq(), SystemCoreClock, HAL_RCC_GetHCLKFreq(),
    //     HAL_RCC_GetPCLK1Freq(), HAL_RCC_GetPCLK2Freq());

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_turbo_obj, mod_passport_System_turbo);

/// def set_user_firmware_pubkey(self, pubkey: buffer) -> None
///     """
///     Set the user firmware public key so the user can install custom firmware
///     """
STATIC mp_obj_t mod_passport_System_set_user_firmware_pubkey(mp_obj_t self, mp_obj_t pubkey) {
    uint8_t          pin_hash[32] = {0};
    mp_buffer_info_t pubkey_info  = {0};
    mp_get_buffer_raise(pubkey, &pubkey_info, MP_BUFFER_READ);

    // uint8_t* p = (uint8_t*)pubkey_info.buf;
    // printf("WRITE: len=%d pubkey=%02x%02x%02x%02x...\n",pubkey_info.len, p[0],  p[1],  p[2], p[3]);

    pinAttempt_t pa_args;
    pa_args.magic_value = PA_MAGIC_V1;
    memcpy(&pa_args.cached_main_pin, g_cached_main_pin, sizeof(g_cached_main_pin));

    // Get the hash that proves user knows the PIN
    int rv = pin_cache_restore(&pa_args, pin_hash);
    if (rv) {
        return mp_const_false;
    }

    // printf("pin hash=%02x%02x%02x%02x...", pin_hash[0], pin_hash[1], pin_hash[2],pin_hash[3]);

    rv = se_encrypted_write(KEYNUM_user_fw_pubkey, KEYNUM_pin_hash, pin_hash, pubkey_info.buf, pubkey_info.len);
    // printf("rv=%d\n", rv);
    return rv == 0 ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_set_user_firmware_pubkey_obj,
                                 mod_passport_System_set_user_firmware_pubkey);

/// def get_user_firmware_pubkey(self, pubkey: bytearray) -> bool:
///     """
///     Get the user firmware public key
///     """
STATIC mp_obj_t mod_passport_System_get_user_firmware_pubkey(mp_obj_t self, mp_obj_t pubkey) {
    uint8_t          buf[72]     = {0};
    mp_buffer_info_t pubkey_info = {0};
    mp_get_buffer_raise(pubkey, &pubkey_info, MP_BUFFER_WRITE);

    if (pubkey_info.len < 64) {
        return mp_const_false;
    }

    se_pair_unlock();
    if (se_read_data_slot(KEYNUM_user_fw_pubkey, buf, sizeof(buf)) == 0) {
        memcpy(pubkey_info.buf, buf, 64);
        return mp_const_true;
    }
    return mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_get_user_firmware_pubkey_obj,
                                 mod_passport_System_get_user_firmware_pubkey);

/// def get_sd_root(self) -> False
///     """
///     Return the path to the microSD card
///     """
STATIC mp_obj_t mod_passport_System_get_sd_root(mp_obj_t self) {
    const char* path = "/sd";
    return mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)path, strlen(path));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_get_sd_root_obj, mod_passport_System_get_sd_root);

/// def is_user_firmware_installed(self) -> None
///     """
///     Check if user firmware is installed or not
///     """
STATIC mp_obj_t mod_passport_System_is_user_firmware_installed(mp_obj_t self) {
    passport_firmware_header_t* fwhdr = (passport_firmware_header_t*)FW_HDR;

    return (fwhdr->signature.pubkey1 == FW_USER_KEY && fwhdr->signature.pubkey2 == 0) ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_is_user_firmware_installed_obj,
                                 mod_passport_System_is_user_firmware_installed);

/// def mod_passport_System_hmac_sha256(self, key, msg, hmac) -> None
///     """
///     Calculate an hmac using the given key and data
///     """
STATIC mp_obj_t mod_passport_System_hmac_sha256(size_t n_args, const mp_obj_t* args) {
    mp_buffer_info_t key_info;
    mp_get_buffer_raise(args[1], &key_info, MP_BUFFER_READ);
    // uint8_t* pkey = (uint8_t*)key_info.buf;
    // printf("key: 0x%02x 0x%02x 0x%02x 0x%02x (len=%d)\n", pkey[0], pkey[1], pkey[2], pkey[3], key_info.len);

    mp_buffer_info_t msg_info;
    mp_get_buffer_raise(args[2], &msg_info, MP_BUFFER_READ);
    // uint8_t* pmsg = (uint8_t*)msg_info.buf;
    // printf("msg: 0x%02x 0x%02x 0x%02x 0x%02x (len=%d)\n", pmsg[0], pmsg[1], pmsg[2], pmsg[3], msg_info.len);
    mp_buffer_info_t hmac_info;
    mp_get_buffer_raise(args[3], &hmac_info, MP_BUFFER_WRITE);
    // printf("hmac:(len=%d)\n", hmac_info.len);

    _hmac_sha256(key_info.buf, key_info.len, msg_info.buf, msg_info.len, hmac_info.buf);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_passport_System_hmac_sha256_obj, 4, 4, mod_passport_System_hmac_sha256);

/// def mod_passport_System_get_serial_number(self) -> None
///     """
///    Get the serial number
///     """
STATIC mp_obj_t mod_passport_System_get_serial_number(mp_obj_t self) {
    char serial[MAX_SERIAL_NUMBER_LEN];

    get_serial_number(serial, MAX_SERIAL_NUMBER_LEN);

    return mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)serial, strlen(serial));
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_get_serial_number_obj, mod_passport_System_get_serial_number);

/// def mod_passport_System_get_device_hash(self, hash) -> None
///     """
///    Get the device hash
///     """
STATIC mp_obj_t mod_passport_System_get_device_hash(mp_obj_t self, mp_obj_t hash) {
    mp_buffer_info_t hash_info;
    mp_get_buffer_raise(hash, &hash_info, MP_BUFFER_WRITE);

    get_device_hash(hash_info.buf);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_get_device_hash_obj, mod_passport_System_get_device_hash);

/// def mod_passport_System_get_backup_pw_hash(self, hash) -> None
///     """
///    Get the hash to use as the "entropy" for the backup password.
///    It's based on the device hash plus the seed.
///     """
STATIC mp_obj_t mod_passport_System_get_backup_pw_hash(mp_obj_t self, mp_obj_t hash) {
    uint8_t device_hash[32];

    mp_buffer_info_t hash_info;
    mp_get_buffer_raise(hash, &hash_info, MP_BUFFER_WRITE);

    get_device_hash(device_hash);
    pinAttempt_t pin_attempt;
    memset(&pin_attempt, 0, sizeof(pinAttempt_t));
    pin_fetch_secret(&pin_attempt);

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, (void*)device_hash, 32);
    sha256_update(&ctx, (void*)pin_attempt.secret, SE_SECRET_LEN);
    sha256_final(&ctx, hash_info.buf);

    // Double SHA
    sha256_init(&ctx);
    sha256_update(&ctx, (void*)hash_info.buf, 32);
    sha256_final(&ctx, hash_info.buf);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_get_backup_pw_hash_obj, mod_passport_System_get_backup_pw_hash);

/// def mod_passport_System_get_rtc_calibration_offset(self) -> Int
///     """
///   Return the calibration offset for the real-time clock.
///     """
STATIC mp_obj_t mod_passport_System_get_rtc_calibration_offset(mp_obj_t self) {
    int32_t offset = eeprom_get_rtc_calibration_offset(0);
    return mp_obj_new_int(offset);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_System_get_rtc_calibration_offset_obj,
                                 mod_passport_System_get_rtc_calibration_offset);

/// def mod_passport_System_set_rtc_calibration_offset(self, Int) -> None
///     """
///   Set the calibration offset for the real-time clock.
///     """
STATIC mp_obj_t mod_passport_System_set_rtc_calibration_offset(mp_obj_t self, mp_obj_t _offset) {
    int32_t offset = mp_obj_get_int(_offset);
    eeprom_set_rtc_calibration_offset(offset);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_set_rtc_calibration_offset_obj,
                                 mod_passport_System_set_rtc_calibration_offset);

/// def mod_passport_System_get_screen_brightness(self) -> Int
///     """
///   Return the saved screen brightness value.
///     """
STATIC mp_obj_t mod_passport_System_get_screen_brightness(mp_obj_t self, mp_obj_t _default) {
    uint16_t default_value = mp_obj_get_int(_default);
    uint16_t brightness    = eeprom_get_screen_brightness(default_value);

    // If it's never been set, then set it to the default
    if (brightness == 0xFFFF) {
        eeprom_set_screen_brightness(default_value);
        brightness = default_value;
    }

    return mp_obj_new_int(brightness);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_get_screen_brightness_obj,
                                 mod_passport_System_get_screen_brightness);

/// def mod_passport_System_set_screen_brightness(self, Int) -> None
///     """
///   Set the screen brightness setting.
///     """
STATIC mp_obj_t mod_passport_System_set_screen_brightness(mp_obj_t self, mp_obj_t _brightness) {
    uint16_t brightness = mp_obj_get_int(_brightness);
    eeprom_set_screen_brightness(brightness);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_set_screen_brightness_obj,
                                 mod_passport_System_set_screen_brightness);

/// def mod_passport_System_busy_wait(self, Int) -> None
///     """
///   Spin in a loop for the specified number of millitseconds.
///     """
STATIC mp_obj_t mod_passport_System_busy_wait(mp_obj_t self, mp_obj_t _delay_ms) {
    uint16_t delay_ms    = mp_obj_get_int(_delay_ms);
    uint32_t start_ticks = mp_hal_ticks_ms();
    uint32_t now_ticks   = 0;

    uint32_t last_refresh_ticks = 0;
    do {
        now_ticks = mp_hal_ticks_ms();
        if (now_ticks - last_refresh_ticks > 50) {
            lv_refresh();
            last_refresh_ticks = now_ticks;
        }
    } while (now_ticks - start_ticks < delay_ms);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_busy_wait_obj, mod_passport_System_busy_wait);

// Simple header verification
STATIC bool verify_header(passport_firmware_header_t* hdr) {
#ifdef SCREEN_MODE_MONO
    if (hdr->info.magic != FW_HEADER_MAGIC) return false;
#elif SCREEN_MODE_COLOR
    if (hdr->info.magic != FW_HEADER_MAGIC_COLOR) return false;
#endif
    if (hdr->info.timestamp == 0) return false;
    if (hdr->info.fwversion[0] == 0x0) return false;
    if (hdr->info.fwlength < FW_HEADER_SIZE) return false;
    if (hdr->info.fwlength > FW_MAX_SIZE) return false;

    // Make sure pubkey indices are in range and are not the same pubkey
    if ((hdr->signature.pubkey1 != FW_USER_KEY) && (hdr->signature.pubkey1 >= FW_MAX_PUB_KEYS)) return false;
    if (hdr->signature.pubkey2 >= FW_MAX_PUB_KEYS) return false;
    if (hdr->signature.pubkey1 == hdr->signature.pubkey2) return false;

    return true;
}

/// def validate_firmware_header(self, header: bytearray) -> None:
///     '''
///     Validate the given firmware header bytes as a potential candidate to be
///     installed.
///     '''
STATIC mp_obj_t mod_passport_System_validate_firmware_header(mp_obj_t self, mp_obj_t header) {
    mp_buffer_info_t header_info;
    mp_get_buffer_raise(header, &header_info, MP_BUFFER_READ);

    // Existing header
    passport_firmware_header_t* fwhdr = (passport_firmware_header_t*)FW_HDR;

    // New header
    passport_firmware_header_t* new_fwhdr = (passport_firmware_header_t*)header_info.buf;

    mp_obj_t tuple[4];

    bool is_valid = verify_header(header_info.buf);

    if (is_valid) {
        // Build the current board hash so we can get the minimum firmware timestamp
        uint8_t current_board_hash[HASH_LEN] = {0};
        get_current_board_hash(current_board_hash);

        uint32_t firmware_timestamp = se_get_firmware_timestamp(current_board_hash);

        // Ensure they are not trying to install an older version of firmware, but allow
        // a reinstall of the same version. Also allow installation of user firmware regardless of
        // timestamp and then allow installing a Foundation-signed build.
        if ((new_fwhdr->signature.pubkey1 != FW_USER_KEY) && (new_fwhdr->info.timestamp < firmware_timestamp)) {
            tuple[0] = mp_const_false;
            tuple[1] = mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)new_fwhdr->info.fwversion,
                                           strlen((const char*)new_fwhdr->info.fwversion));

            // Include an error string
            vstr_t vstr;
            vstr_init(&vstr, 120);

            char* msg = "The selected firmware is older than the currently installed firmware.";
            vstr_add_strn(&vstr, (const char*)msg, strlen(msg));

            vstr_add_strn(&vstr, (const char*)fwhdr->info.fwdate, strlen((const char*)new_fwhdr->info.fwdate));

            msg = "\n\nSelected Version:\n  ";
            vstr_add_strn(&vstr, (const char*)msg, strlen(msg));

            vstr_add_strn(&vstr, (const char*)new_fwhdr->info.fwdate, strlen((const char*)new_fwhdr->info.fwdate));
            tuple[2] = mp_obj_new_str_from_vstr(&mp_type_str, &vstr);

            // Is this user-signed firmware?
            tuple[3] = mp_const_false;

            return mp_obj_new_tuple(4, tuple);
        }
    } else {
        // Invalid header
        tuple[0] = mp_const_false;
        tuple[1] = mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)new_fwhdr->info.fwversion,
                                       strlen((const char*)new_fwhdr->info.fwversion));

        // Include an error string
        vstr_t vstr;
        vstr_init(&vstr, 80);
        char* msg = "The selected firmware header is invalid and cannot be installed.";
        vstr_add_strn(&vstr, (const char*)msg, strlen(msg));
        tuple[2] = mp_obj_new_str_from_vstr(&mp_type_str, &vstr);

        // No header = no user signed firmware
        tuple[3] = mp_const_false;

        return mp_obj_new_tuple(4, tuple);
    }

    // is_valid
    tuple[0] = mp_const_true;

    // Firmware version
    tuple[1] = mp_obj_new_str_copy(&mp_type_str, (const uint8_t*)new_fwhdr->info.fwversion,
                                   strlen((const char*)new_fwhdr->info.fwversion));

    // No error message
    tuple[2] = mp_const_none;

    // Is this user-signed firmware?
    tuple[3] = (new_fwhdr->signature.pubkey1 == FW_USER_KEY) ? mp_const_true : mp_const_false;

    return mp_obj_new_tuple(4, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_validate_firmware_header_obj,
                                 mod_passport_System_validate_firmware_header);

/// def mod_passport_System_enable_lv_refresh(self, Int) -> None
///     """
///   Enable or disable the lv refresh.
///     """
STATIC mp_obj_t mod_passport_System_enable_lv_refresh(mp_obj_t self, mp_obj_t _enable) {
    uint16_t enable    = mp_obj_get_int(_enable);
    lv_refresh_enabled = enable == 0 ? false : true;
    // printf(">>>>> lv_refresh_enabled=%s\r\n", lv_refresh_enabled ? "true" : "false");
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_System_enable_lv_refresh_obj, mod_passport_System_enable_lv_refresh);

STATIC const mp_rom_map_elem_t mod_passport_System_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_reset), MP_ROM_PTR(&mod_passport_System_reset_obj)},
    {MP_ROM_QSTR(MP_QSTR_shutdown), MP_ROM_PTR(&mod_passport_System_shutdown_obj)},
    {MP_ROM_QSTR(MP_QSTR_dispatch), MP_ROM_PTR(&mod_passport_System_dispatch_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_software_info), MP_ROM_PTR(&mod_passport_System_get_software_info_obj)},
    {MP_ROM_QSTR(MP_QSTR_progress_bar), MP_ROM_PTR(&mod_passport_System_progress_bar_obj)},
    {MP_ROM_QSTR(MP_QSTR_turbo), MP_ROM_PTR(&mod_passport_System_turbo_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_user_firmware_pubkey), MP_ROM_PTR(&mod_passport_System_set_user_firmware_pubkey_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_user_firmware_pubkey), MP_ROM_PTR(&mod_passport_System_get_user_firmware_pubkey_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_user_firmware_installed), MP_ROM_PTR(&mod_passport_System_is_user_firmware_installed_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_sd_root), MP_ROM_PTR(&mod_passport_System_get_sd_root_obj)},
    {MP_ROM_QSTR(MP_QSTR_hmac_sha256), MP_ROM_PTR(&mod_passport_System_hmac_sha256_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_serial_number), MP_ROM_PTR(&mod_passport_System_get_serial_number_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_device_hash), MP_ROM_PTR(&mod_passport_System_get_device_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_backup_pw_hash), MP_ROM_PTR(&mod_passport_System_get_backup_pw_hash_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_rtc_calibration_offset), MP_ROM_PTR(&mod_passport_System_get_rtc_calibration_offset_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_rtc_calibration_offset), MP_ROM_PTR(&mod_passport_System_set_rtc_calibration_offset_obj)},
    {MP_ROM_QSTR(MP_QSTR_get_screen_brightness), MP_ROM_PTR(&mod_passport_System_get_screen_brightness_obj)},
    {MP_ROM_QSTR(MP_QSTR_set_screen_brightness), MP_ROM_PTR(&mod_passport_System_set_screen_brightness_obj)},
    {MP_ROM_QSTR(MP_QSTR_busy_wait), MP_ROM_PTR(&mod_passport_System_busy_wait_obj)},
    {MP_ROM_QSTR(MP_QSTR_validate_firmware_header), MP_ROM_PTR(&mod_passport_System_validate_firmware_header_obj)},
    {MP_ROM_QSTR(MP_QSTR_enable_lv_refresh), MP_ROM_PTR(&mod_passport_System_enable_lv_refresh_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_System_locals_dict, mod_passport_System_locals_dict_table);

STATIC const mp_obj_type_t mod_passport_System_type = {
    {&mp_type_type},
    .name        = MP_QSTR_System,
    .make_new    = mod_passport_System_make_new,
    .locals_dict = (void*)&mod_passport_System_locals_dict,
};

STATIC void _hmac_sha256(uint8_t* key, uint32_t key_len, uint8_t* msg, uint32_t msg_len, uint8_t* hmac) {
    uint8_t i_key_pad[SHA256_BLOCK_LENGTH];
    memset(i_key_pad, 0, SHA256_BLOCK_LENGTH);
    memcpy(i_key_pad, key, key_len);

    uint8_t o_key_pad[SHA256_BLOCK_LENGTH];
    for (int i = 0; i < SHA256_BLOCK_LENGTH; i++) {
        o_key_pad[i] = i_key_pad[i] ^ 0x5c;
        i_key_pad[i] ^= 0x36;
    }

    // First hash
    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, i_key_pad, SHA256_BLOCK_LENGTH);
    memset(i_key_pad, 0, SHA256_BLOCK_LENGTH);

    // Add the data
    sha256_update(&ctx, msg, msg_len);

    // Hash
    sha256_final(&ctx, hmac);

    // Second hash
    sha256_init(&ctx);
    sha256_update(&ctx, o_key_pad, SHA256_BLOCK_LENGTH);
    sha256_update(&ctx, hmac, SHA256_DIGEST_LENGTH);
    sha256_final(&ctx, hmac);
}