// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <string.h>

#include "py/obj.h"
#include "py/runtime.h"
#include "py/mphal.h"

#include "camera-ovm7690.h"
#include "image_conversion.h"

#ifdef SCREEN_MODE_COLOR
STATIC void swizzle_u16(uint16_t* buffer, int w, int h);
#endif

/// package: passport.camera

/// def enable() -> None:
///     """
///     Turn on the camera in preparation for calling snapshot().
///     """
STATIC mp_obj_t mod_passport_camera_enable(void) {
    HAL_StatusTypeDef status = HAL_OK;

    framebuffer_camera_lock();

    // Clear to black before use or else we get remnants of the UI skewed into the camera view
    uint8_t* fb = (uint8_t*)framebuffer_camera();
    memset(fb, 0, CAMERA_HOR_RES * CAMERA_VER_RES * sizeof(uint16_t));

    if ((status = camera_on()) != HAL_OK) {
        mp_hal_raise(status);
        return mp_const_none;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_camera_enable_obj, mod_passport_camera_enable);

/// def disable() -> None:
///     """
///     Turn off the camera.
///     """
STATIC mp_obj_t mod_passport_camera_disable(void) {
    HAL_StatusTypeDef status = HAL_OK;

    framebuffer_camera_unlock();
    if ((status = camera_off()) != HAL_OK) {
        mp_hal_raise(status);
        return mp_const_none;
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_camera_disable_obj, mod_passport_camera_disable);

/// def snapshot(self) -> None:
///     """
///     Start a snapshot and wait for it to finish, then convert and copy it into the provided image buffers.
///     """
STATIC mp_obj_t mod_passport_camera_snapshot(void) {
    HAL_StatusTypeDef status = HAL_OK;

    // Lock the framebuffer.
    if ((status = camera_snapshot()) != HAL_OK) {
        mp_hal_raise(status);
        return mp_const_none;
    }

    // SAFETY: framebuffer_camera() is valid as camera_snapshot() checks
    // that the address is not NULL.
    uint16_t *framebuffer = framebuffer_camera();

#ifdef SCREEN_MODE_COLOR
    swizzle_u16(framebuffer, CAMERA_HOR_RES, CAMERA_VER_RES);
#endif  // SCREEN_MODE_COLOR

    // Remove vertical line from the camera.
    for (int y = 0; y < CAMERA_VER_RES; y++) {
        int line = y * CAMERA_HOR_RES;
        framebuffer[line + 350] = framebuffer[line + 349];
        framebuffer[line + 351] = framebuffer[line + 349];
        framebuffer[line + 352] = framebuffer[line + 353];
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_camera_snapshot_obj, mod_passport_camera_snapshot);

/// def resize(new_hor_res: int, new_ver_res: int) -> None:
///     """
///     Resize by nearest neighbor the last camera snapshot.
///
///     :raises: ValueError
///     """
STATIC mp_obj_t mod_passport_camera_resize(mp_obj_t new_hor_res_obj, mp_obj_t new_ver_res_obj) {
    const uint32_t old_hor_res = CAMERA_HOR_RES;
    const uint32_t old_ver_res = CAMERA_VER_RES;
    const uint32_t new_hor_res = mp_obj_get_int(new_hor_res_obj);
    const uint32_t new_ver_res = mp_obj_get_int(new_ver_res_obj);

    if (new_hor_res > CAMERA_HOR_RES || new_ver_res > CAMERA_VER_RES) {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid resize resolution"));
    }

    uint8_t* framebuffer = NULL;
    if ((framebuffer = (uint8_t*)framebuffer_camera()) == NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("Could not get framebuffer, camera is disabled"));
    }

    // Approximation of:
    // - (double)old_hor_res / (double)new_hor_res
    // - (double)old_ver_res / (double)new_ver_res
    //
    // Bit shifts 16 bits to the right the initial value to avoid using
    // floating point numbers. Incurs a possible small precision error when
    // multiplying it.
    uint32_t x_ratio = ((old_hor_res << 16) / new_hor_res) + 1;
    uint32_t y_ratio = ((old_ver_res << 16) / new_ver_res) + 1;
    for (uint32_t dst_y = 0; dst_y < new_ver_res; dst_y++) {
        for (uint32_t dst_x = 0; dst_x < new_hor_res; dst_x++) {
            // Ratio is multiplied by each point value, then shifted to the left
            // to recover the value.
            uint32_t src_x = ((uint32_t)dst_x * (uint32_t)x_ratio) >> 16;
            uint32_t src_y = ((uint32_t)dst_y * (uint32_t)y_ratio) >> 16;

            uint32_t src_pixel = (src_y * old_hor_res * sizeof(uint16_t)) + (src_x * sizeof(uint16_t));
            uint32_t dst_pixel = (dst_y * new_hor_res * sizeof(uint16_t)) + (dst_x * sizeof(uint16_t));

            // Copy from old destination to new destination.
            framebuffer[dst_pixel + 0] = framebuffer[src_pixel + 0];
            framebuffer[dst_pixel + 1] = framebuffer[src_pixel + 1];
        }
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_passport_camera_resize_obj, mod_passport_camera_resize);

/// def framebuffer() -> bytearray:
///     """
///     Return the camera framebuffer as a bytearray.
///     """
STATIC mp_obj_t mod_passport_camera_framebuffer(void) {
    uint16_t* framebuffer = NULL;
    if ((framebuffer = framebuffer_camera()) == NULL) {
        mp_raise_ValueError(MP_ERROR_TEXT("Could not get framebuffer, camera is disabled"));
        return mp_const_none;
    }

    return mp_obj_new_bytearray_by_ref(CAMERA_FRAMEBUFFER_SIZE, framebuffer);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_passport_camera_framebuffer_obj, mod_passport_camera_framebuffer);

STATIC const mp_rom_map_elem_t mod_passport_camera_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_HOR_RES), MP_ROM_INT(CAMERA_HOR_RES)},
    {MP_ROM_QSTR(MP_QSTR_VER_RES), MP_ROM_INT(CAMERA_VER_RES)},
    {MP_ROM_QSTR(MP_QSTR_enable), MP_ROM_PTR(&mod_passport_camera_enable_obj)},
    {MP_ROM_QSTR(MP_QSTR_disable), MP_ROM_PTR(&mod_passport_camera_disable_obj)},
    {MP_ROM_QSTR(MP_QSTR_snapshot), MP_ROM_PTR(&mod_passport_camera_snapshot_obj)},
    {MP_ROM_QSTR(MP_QSTR_resize), MP_ROM_PTR(&mod_passport_camera_resize_obj)},
    {MP_ROM_QSTR(MP_QSTR_framebuffer), MP_ROM_PTR(&mod_passport_camera_framebuffer_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_camera_globals, mod_passport_camera_globals_table);

STATIC const mp_obj_module_t mod_passport_camera_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mod_passport_camera_globals,
};

#ifdef SCREEN_MODE_COLOR
STATIC void swizzle_u16(uint16_t* buffer, int w, int h) {
    uint16_t* end = buffer + (w * h);

    while (buffer < end) {
        uint16_t c = __builtin_bswap16(*buffer);
        uint16_t b = (c & 0xF800) >> 11;
        uint16_t g = c & 0x07E0;
        uint16_t r = (c & 0x001F) << 11;
        *buffer    = __builtin_bswap16(r | g | b);
        buffer++;
    }
}
#endif
