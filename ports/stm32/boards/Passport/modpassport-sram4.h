// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <stdint.h>

#include "py/obj.h"
#include "py/objarray.h"

#include "../../../../lib/lv_bindings/lvgl/lvgl.h"

#include "framebuffer.h"

/**
 * @brief Passport maximum supported QR version that can be rendered.
 *
 * @note Keep in sync with modfoundation.c QRCode class.
 */
#define PASSPORT_MAX_QR_VERSION (13)

/**
 * @brief Attribute used to allocate a static variable in the
 *        SRAM4 section.
 */
#define MP_SRAM4 __attribute__((section(".sram4")))

/**
 * @brief Create a compile-time bytearray by reference.
 *
 * Same behaviour as `mp_obj_new_bytearray_by_ref` (bytearray_at in Python side)
 * but statically allocated.
 *
 * @param obj The object name.
 * @param ptr The pointer to the data.
 * @param len The length of the data.
 */
#define MP_OBJ_BYTEARRAY_BY_REF(obj, ptr, ptr_len)  \
    mp_obj_array_t obj = {                          \
        .base = {&mp_type_bytearray},               \
        .typecode = BYTEARRAY_TYPECODE,             \
        .free = 0,                                  \
        .len = ptr_len,                             \
        .items = ptr,                               \
    }

/// package: passport.sram4

/// ext_settings_buf: bytearray
STATIC MP_SRAM4 uint8_t mod_passport_sram4_ext_settings_buf[16 * 1024];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_sram4_ext_settings_buf_obj,
                               mod_passport_sram4_ext_settings_buf,
                               sizeof(mod_passport_sram4_ext_settings_buf));

/// tmp_buf: bytearray
STATIC MP_SRAM4 uint8_t mod_passport_sram4_tmp_buf[1024];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_sram4_tmp_buf_obj,
                               mod_passport_sram4_tmp_buf,
                               sizeof(mod_passport_sram4_tmp_buf));
/// psbt_tmp256: bytearray
STATIC MP_SRAM4 uint8_t mod_passport_psbt_tmp256[256];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_sram4_psbt_tmp256_obj,
                               mod_passport_psbt_tmp256,
                               sizeof(mod_passport_psbt_tmp256));

/// qrcode_buffer: bytearray
STATIC MP_SRAM4 uint8_t mod_passport_sram4_qrcode_buffer[LV_QRCODE_IMG_BUF_SIZE(LCD_HOR_RES)];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_sram4_passport_qrcode_buffer_obj,
                               mod_passport_sram4_qrcode_buffer,
                               sizeof(mod_passport_sram4_qrcode_buffer));

/// qrcode_modules_buffer: bytearray
STATIC MP_SRAM4 uint8_t mod_passport_sram4_qrcode_modules_buffer[LV_QRCODE_MODULES_BUF_SIZE(PASSPORT_MAX_QR_VERSION)];
STATIC MP_OBJ_BYTEARRAY_BY_REF(mod_passport_sram4_qrcode_modules_buffer_obj,
                               mod_passport_sram4_qrcode_modules_buffer,
                               sizeof(mod_passport_sram4_qrcode_modules_buffer));

/// def qrcode_buffer_clear() -> None:
///     """
///     Clear the QR code buffer
///
///     Sets all bytes to 0, except the color palette which is at the start of the buffer (4 * 2 bytes).
///     """
STATIC mp_obj_t mod_passport_sram4_qrcode_buffer_clear(void)
{
    memset(mod_passport_sram4_qrcode_buffer + (4 * 2), 0, sizeof(mod_passport_sram4_qrcode_buffer) - (4 * 2));
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_sram4_qrcode_buffer_clear_obj,
                                mod_passport_sram4_qrcode_buffer_clear);

STATIC const mp_rom_map_elem_t mod_passport_sram4_globals_table[] = {
        {MP_ROM_QSTR(MP_QSTR_MAX_QR_VERSION), MP_ROM_INT(PASSPORT_MAX_QR_VERSION)},
        {MP_ROM_QSTR(MP_QSTR_ext_settings_buf), MP_ROM_PTR(&mod_passport_sram4_ext_settings_buf_obj)},
        {MP_ROM_QSTR(MP_QSTR_tmp_buf), MP_ROM_PTR(&mod_passport_sram4_tmp_buf_obj)},
        {MP_ROM_QSTR(MP_QSTR_psbt_tmp256), MP_ROM_PTR(&mod_passport_sram4_psbt_tmp256_obj)},
        {MP_ROM_QSTR(MP_QSTR_qrcode_buffer), MP_ROM_PTR(&mod_passport_sram4_passport_qrcode_buffer_obj)},
        {MP_ROM_QSTR(MP_QSTR_qrcode_modules_buffer), MP_ROM_PTR(&mod_passport_sram4_qrcode_modules_buffer_obj)},
        {MP_ROM_QSTR(MP_QSTR_qrcode_buffer_clear), MP_ROM_PTR(&mod_passport_sram4_qrcode_buffer_clear_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_sram4_globals, mod_passport_sram4_globals_table);

STATIC const mp_obj_module_t mod_passport_sram4_module = {
        .base    = {&mp_type_module},
        .globals = (mp_obj_dict_t*)&mod_passport_sram4_globals,
};
