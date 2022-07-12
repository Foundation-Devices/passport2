// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include "py/obj.h"
#include "py/runtime.h"
#include "flash.h"

#ifdef SCREEN_MODE_MONO

#ifndef SETTINGS_FLASH_DEBUG
#define SETTINGS_FLASH_DEBUG    0
#endif

#define SETTINGS_FLASH_START    (0x81E0000)
#define SETTINGS_FLASH_SIZE     (0x20000)
#define SETTINGS_FLASH_END      (SETTINGS_FLASH_START + SETTINGS_FLASH_SIZE - 1)

/// package: passport

/// class SettingsFlash:
///     """
///     Internal flash settings.
///     """
typedef struct _mp_obj_SettingsFlash_t {
    mp_obj_base_t base;
} mp_obj_SettingsFlash_t;

/// def __init__(self) -> None:
///     '''
///     Initialize SettingsFlash context.
///     '''
STATIC mp_obj_t mod_passport_SettingsFlash_make_new(const mp_obj_type_t* type,
                                                    size_t               n_args,
                                                    size_t               n_kw,
                                                    const mp_obj_t*      args) {
    mp_obj_SettingsFlash_t* o = m_new_obj(mp_obj_SettingsFlash_t);
    o->base.type              = type;
    return MP_OBJ_FROM_PTR(o);
}

/// def write(self, addr: int, data: buffer) -> None:
///     """
///     Write data to internal flash
///     """
STATIC mp_obj_t mod_passport_SettingsFlash_write(mp_obj_t self,
                                                 mp_obj_t addr_obj,
                                                 mp_obj_t data_obj) {
    mp_uint_t addr              = mp_obj_get_int(addr_obj);
    mp_buffer_info_t data_info  = {0};
    mp_get_buffer_raise(data_obj, &data_info, MP_BUFFER_READ);

    if (addr < SETTINGS_FLASH_START ||
        addr + data_info.len - 1 > SETTINGS_FLASH_END ||
        data_info.len % 4 != 0) {
#if SETTINGS_FLASH_DEBUG
        printf("[passport.SettingsFlash]: bad parameters: flash_addr=0x%08lx\nSETTINGS_FLASH_START=0x%08x\nSETTINGS_FLASH_END=0x%08x\ndata_info.len=0x%04x\n",
               flash_addr, SETTINGS_FLASH_START, SETTINGS_FLASH_END, data_info.len);
#endif
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid parameters"));
        return mp_const_none;
    }

#if SETTINGS_FLASH_DEBUG
    printf("[passport.SettingsFlash] writing %u bytes to 0x%08x\n", (unsigned)data_info.len, (unsigned)addr);

    for (uint32_t i = 0; i < data_info.len;) {
        uint8_t tmp = (uint8_t*)data_info.buf;
        printf("%02x ", tmp[i]);
        i++;
        if (i % 32 == 0) {
            printf("\n");
        }
    }
#endif

    // NOTE: This function doesn't return any error/success info
    flash_write(addr, data_info.buf, data_info.len / 4);

#if SETTINGS_FLASH_DEBUG
    printf("[passport.SettingsFlash] write done\n");
#endif
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(mod_passport_SettingsFlash_write_obj, mod_passport_SettingsFlash_write);


/// def erase(self) -> None
///     """
///     Erase all of flash (H7 doesn't provide facility to erase less than the whole 128K)
///     """
STATIC mp_obj_t mod_passport_SettingsFlash_erase(mp_obj_t self) {
#if SETTINGS_FLASH_DEBUG
    printf("[passport.SettingsFlash] erase\n");
#endif

    // NOTE: This function doesn't return any error/success info
    flash_erase(SETTINGS_FLASH_START, SETTINGS_FLASH_SIZE / 4);

    return mp_const_true;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(mod_passport_SettingsFlash_erase_obj, mod_passport_SettingsFlash_erase);

STATIC const mp_rom_map_elem_t mod_passport_SettingsFlash_locals_dict_table[] = {
    {MP_ROM_QSTR(MP_QSTR_START),    MP_ROM_INT(SETTINGS_FLASH_START)},
    {MP_ROM_QSTR(MP_QSTR_END),      MP_ROM_INT(SETTINGS_FLASH_END)},
    {MP_ROM_QSTR(MP_QSTR_write),    MP_ROM_PTR(&mod_passport_SettingsFlash_write_obj)},
    {MP_ROM_QSTR(MP_QSTR_erase),    MP_ROM_PTR(&mod_passport_SettingsFlash_erase_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_passport_SettingsFlash_locals_dict, mod_passport_SettingsFlash_locals_dict_table);

STATIC const mp_obj_type_t mod_passport_SettingsFlash_type = {
    {&mp_type_type},
    .name        = MP_QSTR_SettingsFlash,
    .make_new    = mod_passport_SettingsFlash_make_new,
    .locals_dict = (void*)&mod_passport_SettingsFlash_locals_dict,
};

#endif