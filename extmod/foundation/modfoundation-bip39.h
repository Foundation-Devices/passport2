// SPDX-FileCopyrightText: 2022 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <string.h>

#include "py/obj.h"
#include "py/objstr.h"
#include "py/runtime.h"

#include "bip39.h"
#include "bip39_utils.h"

#define MATCHES_LEN 80

extern word_info_t bip39_word_info[];
extern word_info_t bytewords_word_info[]; // TODO: Restructure this so bip39 and bytewords are separate

/// package: foundation.bip39

/// def get_words_matching_prefix(self, prefix, max_matches, word_list) -> None
///     '''
///     Return a comma-separated list of BIP39 seed words that match the given keypad
///     digits prefix (e.g., '222').
///     '''
STATIC mp_obj_t mod_foundation_bip39_get_words_matching_prefix(size_t n_args, const mp_obj_t *args)
{
    mp_check_self(mp_obj_is_str_or_bytes(args[0]));
    GET_STR_DATA_LEN(args[0], prefix_str, prefix_len);

    int max_matches = mp_obj_get_int(args[1]);

    // Must be "bip39" or "bytewords"
    mp_check_self(mp_obj_is_str_or_bytes(args[2]));
    GET_STR_DATA_LEN(args[2], word_list_str, word_list_len);

    const word_info_t *word_info = NULL;
    uint32_t num_words = 0;
    if (strcmp("bip39", (char *)word_list_str) == 0)
    {
        word_info = bip39_word_info;
        num_words = 2048;
    }
    else if (strcmp("bytewords", (char *)word_list_str) == 0)
    {
        word_info = bytewords_word_info;
        num_words = 256;
    }
    else
    {
        return mp_const_none;
    }

    char matches[MATCHES_LEN];

    get_words_matching_prefix((char *)prefix_str, matches, MATCHES_LEN, max_matches, word_info, num_words);

    // Return the string
    vstr_t vstr;
    int matches_len = strlen((const char *)matches);

    vstr_init(&vstr, matches_len + 1);
    vstr_add_strn(&vstr, (const char *)matches, matches_len);

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_foundation_bip39_get_words_matching_prefix_obj,
                                           3,
                                           3,
                                           mod_foundation_bip39_get_words_matching_prefix);

/// def mnemonic_to_bits(self) -> None
///     '''
///     Call trezorcrypto's mnemonic_to_bits() C function since it's not exposed
///     through their Python interface.
///     '''
STATIC mp_obj_t mod_foundation_bip39_mnemonic_to_bits(mp_obj_t mnemonic, mp_obj_t entropy)
{
    mp_check_self(mp_obj_is_str_or_bytes(mnemonic));
    GET_STR_DATA_LEN(mnemonic, mnemonic_str, mnemonic_len);
    mp_buffer_info_t entropy_info;
    mp_get_buffer_raise(entropy, &entropy_info, MP_BUFFER_WRITE);

    int len = mnemonic_to_bits((const char *)mnemonic_str, entropy_info.buf);
    return mp_obj_new_int(len);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_bip39_mnemonic_to_bits_obj, mod_foundation_bip39_mnemonic_to_bits);

STATIC const mp_rom_map_elem_t mod_foundation_bip39_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_get_words_matching_prefix), MP_ROM_PTR(&mod_foundation_bip39_get_words_matching_prefix_obj)},
    {MP_ROM_QSTR(MP_QSTR_mnemonic_to_bits), MP_ROM_PTR(&mod_foundation_bip39_mnemonic_to_bits_obj)},
};
STATIC MP_DEFINE_CONST_DICT(mod_foundation_bip39_globals, mod_foundation_bip39_globals_table);

STATIC const mp_obj_module_t mod_foundation_bip39_module = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&mod_foundation_bip39_globals,
};