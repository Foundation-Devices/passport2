// SPDX-FileCopyrightText: © 2024 Foundation Devices, Inc. <hello@foundation.xyz>
// SPDX-License-Identifier: GPL-3.0-or-later

#include "foundation.h"

#include "py/obj.h"

/// class FlashError(Exception):
///     """
///     """
STATIC MP_DEFINE_EXCEPTION(FlashError, Exception);

STATIC mp_obj_t mod_foundation_flash_read(mp_obj_t offset_obj, mp_obj_t data)
{
    mp_buffer_info_t data_info;
    mp_get_buffer_raise(data, &data_info, MP_BUFFER_WRITE);
    mp_int_t offset = mp_obj_get_int(offset_obj);

    if (!foundation_flash_read(offset, data_info.buf, data_info.len)) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to read from SPI flash"));
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_flash_read_obj, mod_foundation_flash_read);

STATIC mp_obj_t mod_foundation_flash_write(mp_obj_t offset_obj, mp_obj_t data)
{
    mp_buffer_info_t data_info;
    mp_get_buffer_raise(data, &data_info, MP_BUFFER_READ);
    mp_int_t offset = mp_obj_get_int(offset_obj);

    if (!foundation_flash_write(offset, data_info.buf, data_info.len)) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to write from SPI flash"));
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_flash_write_obj, mod_foundation_flash_write);

STATIC mp_obj_t mod_foundation_flash_sector_erase(mp_obj_t offset_obj)
{
    mp_int_t offset = mp_obj_get_int(offset_obj);

    if (!foundation_flash_sector_erase(offset)) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to erase sector from SPI flash"));
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_flash_sector_erase_obj, mod_foundation_flash_sector_erase);

STATIC mp_obj_t mod_foundation_flash_block_erase(mp_obj_t offset_obj)
{
    mp_int_t offset = mp_obj_get_int(offset_obj);

    if (!foundation_flash_block_erase(offset)) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to erase block from SPI flash"));
    }
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_foundation_flash_block_erase_obj, mod_foundation_flash_block_erase);

STATIC mp_obj_t mod_foundation_flash_is_busy(void)
{
    bool is_busy = false;

    if (!foundation_flash_is_busy(&is_busy)) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to retrieve status from SPI flash"));
    }
    return is_busy ? mp_const_true : mp_const_false;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_flash_is_busy_obj, mod_foundation_flash_is_busy);

STATIC mp_obj_t mod_foundation_flash_wait_done(void)
{
    if (!foundation_flash_wait_done()) {
        mp_raise_msg(&mp_type_FlashError, MP_ERROR_TEXT("failed to flush SPI flash"));
    }

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_0(mod_foundation_flash_wait_done_obj, mod_foundation_flash_wait_done);

STATIC const mp_rom_map_elem_t mod_foundation_flash_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mod_foundation_flash_read_obj)},
    {MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mod_foundation_flash_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_sector_erase), MP_ROM_PTR(&mod_foundation_flash_sector_erase_obj)},
    {MP_ROM_QSTR(MP_QSTR_block_erase), MP_ROM_PTR(&mod_foundation_flash_block_erase_obj)},
    {MP_ROM_QSTR(MP_QSTR_is_busy), MP_ROM_PTR(&mod_foundation_flash_is_busy_obj)},
    {MP_ROM_QSTR(MP_QSTR_wait_done), MP_ROM_PTR(&mod_foundation_flash_wait_done_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_flash_globals, mod_foundation_flash_globals_table);

STATIC const mp_obj_module_t mod_foundation_flash_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_flash_globals,
};
