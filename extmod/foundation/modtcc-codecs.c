// SPDX-FileCopyrightText: © 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// SPDX-FileCopyrightText: 2018 Coinkite, Inc. <coldcardwallet.com>
// SPDX-License-Identifier: GPL-3.0-only
//
/*
 * Copyright (c) 2018 Coinkite Inc.
 *
 * Licensed under GNU License
 * see LICENSE file for details
 *
 *
 * Various encodes/decoders/serializers: base58, base32, bech32, etc.
 *
 */

#include <stdint.h>
#include <stdio.h>
#include <string.h>

#include "py/runtime.h"

#include "py/objstr.h"

#include "base32.h"
#include "base58.h"
#include "hasher.h"
#include "segwit_addr.h"

//
// Base 58
//

STATIC mp_obj_t modtcc_b58_encode(mp_obj_t data) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
    if (buf.len == 0) {
        // there is an encoding for empty string (4 bytes of fixed checksum) but not useful
        mp_raise_ValueError(NULL);
    }

    vstr_t vstr;
    vstr_init_len(&vstr, (buf.len * 2) + 10);

    // Do double SHA on the hash
    int rl = base58_encode_check(buf.buf, buf.len, HASHER_SHA2D, vstr.buf, vstr.len);

    if (rl < 1) {
        // unlikely
        mp_raise_ValueError(NULL);
    }

    vstr.len = rl - 1;  // strip NUL

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(modtcc_b58_encode_obj, modtcc_b58_encode);

STATIC mp_obj_t modtcc_b58_decode(mp_obj_t enc) {
    const char* s = mp_obj_str_get_str(enc);

    uint8_t tmp[128];

    int rl = base58_decode_check(s, HASHER_SHA2D, tmp, sizeof(tmp));

    if (rl <= 0) {
        // transcription error from user is very likely
        mp_raise_ValueError(MP_ERROR_TEXT("corrupt base58"));
    }

    return mp_obj_new_bytes(tmp, rl);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(modtcc_b58_decode_obj, modtcc_b58_decode);

//
// Base 32
//

STATIC mp_obj_t modtcc_b32_encode(mp_obj_t data) {
    mp_buffer_info_t buf;
    mp_get_buffer_raise(data, &buf, MP_BUFFER_READ);
    if (buf.len == 0) {
        return mp_const_empty_bytes;
    }

    vstr_t vstr;
    vstr_init_len(&vstr, (buf.len * 2) + 10);

    char* last = base32_encode(buf.buf, buf.len, vstr.buf, vstr.len, BASE32_ALPHABET_RFC4648);

    if (!last) {
        // unlikely
        mp_raise_ValueError(NULL);
    }

    vstr.len = last - vstr.buf;  // strips NUL

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(modtcc_b32_encode_obj, modtcc_b32_encode);

STATIC mp_obj_t modtcc_b32_decode(mp_obj_t enc) {
    const char* s = mp_obj_str_get_str(enc);

    uint8_t tmp[256];

    uint8_t* last = base32_decode(s, strlen(s), tmp, sizeof(tmp), BASE32_ALPHABET_RFC4648);

    if (!last) {
        // transcription error from user is very likely
        mp_raise_ValueError(MP_ERROR_TEXT("corrupt base32"));
    }

    return mp_obj_new_bytes(tmp, last - tmp);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(modtcc_b32_decode_obj, modtcc_b32_decode);

//
//
// Bech32 aka. Segwit addresses, but hopefylly not specific to segwit addresses only.
//
//

// pack and unpack bits; probably 5 or 8...
//
STATIC inline int sw_convert_bits(
    uint8_t* out, size_t* outlen, const int outbits, const uint8_t* in, size_t inlen, const int inbits, bool pad) {
    uint32_t val  = 0;
    int      bits = 0;
    uint32_t maxv = (((uint32_t)1) << outbits) - 1;
    while (inlen--) {
        val = (val << inbits) | *(in++);
        bits += inbits;
        while (bits >= outbits) {
            bits -= outbits;
            out[(*outlen)++] = (val >> bits) & maxv;
        }
    }
    if (pad) {
        if (bits) {
            out[(*outlen)++] = (val << (outbits - bits)) & maxv;
        }
    } else if (((val << (outbits - bits)) & maxv) || bits >= inbits) {
        return 0;
    }

    return 1;
}

STATIC mp_obj_t modtcc_bech32_encode(mp_obj_t hrp_obj, mp_obj_t segwit_version_obj, mp_obj_t data_obj) {
    const char*    hrp            = mp_obj_str_get_str(hrp_obj);
    const uint32_t segwit_version = mp_obj_int_get_checked(segwit_version_obj);

    mp_buffer_info_t buf;
    mp_get_buffer_raise(data_obj, &buf, MP_BUFFER_READ);

    // low-level bech32 functions want 5-bit data unpacked into bytes. first value is
    // the version number (5 bits), and remainder is packed data.

    if (segwit_version > 16) {
        mp_raise_ValueError(MP_ERROR_TEXT("sw version"));
    }

    uint8_t *data    = m_new(uint8_t, buf.len + 1);
    size_t  data_len = 0;
    data[0]          = segwit_version;
    int cv_ok        = sw_convert_bits(data + 1, &data_len, 5, buf.buf, buf.len, 8, true);

    if (cv_ok != 1) {
        m_del(uint8_t, data, buf.len + 1);
        mp_raise_ValueError(MP_ERROR_TEXT("pack fail"));
    }

    // we already prefixed the version number
    data_len += 1;

    vstr_t vstr;
    vstr_init_len(&vstr, strlen(hrp) + data_len + 8);

    int rv = bech32_encode(vstr.buf, hrp, data, data_len, BECH32_ENCODING_BECH32);
    if (rv != 1) {
        m_del(uint8_t, data, buf.len + 1);
        mp_raise_ValueError(MP_ERROR_TEXT("encode fail"));
    }
    m_del(uint8_t, data, buf.len + 1);
    vstr.len = strlen(vstr.buf);

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_3(modtcc_bech32_encode_obj, modtcc_bech32_encode);

STATIC mp_obj_t modtcc_bech32_decode(mp_obj_t enc) {
    const char* s = mp_obj_str_get_str(enc);

    /** Decode a Bech32 string
 *
 *  Out: hrp:      Pointer to a buffer of size strlen(input) - 6. Will be
 *                 updated to contain the null-terminated human readable part.
 *       data:     Pointer to a buffer of size strlen(input) - 8 that will
 *                 hold the encoded 5-bit data values.
 *       data_len: Pointer to a size_t that will be updated to be the number
 *                 of entries in data.
 *  In: input:     Pointer to a null-terminated Bech32 string.
 *  Returns 1 if succesful.
int bech32_decode(
    char *hrp,
    uint8_t *data,
    size_t *data_len,
    const char *input
);
 */

    char    hrp[strlen(s) + 16];
    uint8_t tmp[strlen(s) + 16];  // actually 8-bit
    size_t  tmp_len = 0;

    int rv = bech32_decode(hrp, tmp, &tmp_len, s);

    if (rv != 1) {
        // probably transcription error from user
        mp_raise_ValueError(MP_ERROR_TEXT("corrupt bech32"));
    }

    if (tmp_len <= 1) {
        // lots of valid Bech32 strings, but invalid for segwit puposes
        // can end up here; but don't care.
        mp_raise_ValueError(MP_ERROR_TEXT("no sw verion and/or data"));
    }

    // re-pack 5-bit data into 8-bit bytes (after version)
    #pragma GCC diagnostic push
    #pragma GCC diagnostic ignored "-Wvla-larger-than="
    uint8_t packed[tmp_len];
    #pragma GCC diagnostic pop
    size_t  packed_len = 0;

    int cv_ok = sw_convert_bits(packed, &packed_len, 8, tmp + 1, tmp_len - 1, 5, false);

    if (cv_ok != 1) {
        mp_raise_ValueError(MP_ERROR_TEXT("repack fail"));
    }

    // return a tuple: (hrp, version, data)
    mp_obj_t tuple[3] = {
        mp_obj_new_str(hrp, strlen(hrp)),
        MP_OBJ_NEW_SMALL_INT(tmp[0]),
        mp_obj_new_bytes(packed, packed_len),
    };

    return mp_obj_new_tuple(3, tuple);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(modtcc_bech32_decode_obj, modtcc_bech32_decode);

STATIC const mp_rom_map_elem_t modtcc_codecs_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_codecs)},
    {MP_ROM_QSTR(MP_QSTR_b58_encode), MP_ROM_PTR(&modtcc_b58_encode_obj)},
    {MP_ROM_QSTR(MP_QSTR_b58_decode), MP_ROM_PTR(&modtcc_b58_decode_obj)},
    {MP_ROM_QSTR(MP_QSTR_b32_encode), MP_ROM_PTR(&modtcc_b32_encode_obj)},
    {MP_ROM_QSTR(MP_QSTR_b32_decode), MP_ROM_PTR(&modtcc_b32_decode_obj)},
    {MP_ROM_QSTR(MP_QSTR_bech32_encode), MP_ROM_PTR(&modtcc_bech32_encode_obj)},
    {MP_ROM_QSTR(MP_QSTR_bech32_decode), MP_ROM_PTR(&modtcc_bech32_decode_obj)},
};
STATIC MP_DEFINE_CONST_DICT(modtcc_codecs_globals, modtcc_codecs_globals_table);

STATIC const mp_obj_module_t modtcc_codecs_module = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&modtcc_codecs_globals,
};

// Top level

STATIC const mp_rom_map_elem_t mp_module_tcc_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR_codecs), MP_ROM_PTR(&modtcc_codecs_module)},
};
STATIC MP_DEFINE_CONST_DICT(mp_module_tcc_globals, mp_module_tcc_globals_table);

const mp_obj_module_t mp_module_tcc = {
    .base    = {&mp_type_module},
    .globals = (mp_obj_dict_t*)&mp_module_tcc_globals,
};

MP_REGISTER_MODULE(MP_QSTR_tcc, mp_module_tcc, 1);

// EOF
