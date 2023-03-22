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
 * Various encodes/decoders/serializers: base58, bech32, etc.
 *
 */

#include <stdint.h>
#include <string.h>

#include "py/runtime.h"

#include "py/objstr.h"

#include "base58.h"
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

//
//
// Bech32 aka. Segwit addresses, but hopefylly not specific to segwit addresses only.
//
//

// pack and unpack bits; probably 5 or 8...
//
STATIC inline int sw_convert_bits(
    uint8_t* out, size_t* outlen, const int outbits, const uint8_t* in, size_t inlen, const int inbits, bool pad, size_t limit) {
    uint32_t val  = 0;
    int      bits = 0;
    uint32_t maxv = (((uint32_t)1) << outbits) - 1;
    *outlen = 0;
    while (inlen--) {
        val = (val << inbits) | *(in++);
        bits += inbits;
        while (bits >= outbits) {
            bits -= outbits;
            if (*outlen == limit) {
                return 0;
            }
            out[(*outlen)++] = (val >> bits) & maxv;
        }
    }
    if (pad) {
        if (bits) {
            if (*outlen == limit) {
                return 0;
            }
            out[(*outlen)++] = (val << (outbits - bits)) & maxv;
        }
    } else if (((val << (outbits - bits)) & maxv) || bits >= inbits) {
        return 0;
    }

    return 1;
}

STATIC inline int sw_convert_bits_buffer_size(
    const int outbits, size_t inlen, const int inbits, bool pad) {
    // number of bits input
    size_t in_total = inlen * inbits;
    // number of bytes to fit output bits in new base
    size_t out_total = in_total / outbits;

    // add 1 if padding is included and necessary
    if (pad && (in_total % out_total)) {
        out_total++;
    }

    return out_total;
}

STATIC mp_obj_t modtcc_bech32_encode(size_t n_args, const mp_obj_t *args) {
    const char*    hrp            = mp_obj_str_get_str(args[0]);
    const uint32_t segwit_version = mp_obj_int_get_checked(args[1]);
    uint32_t       bech32_version = BECH32_ENCODING_BECH32;

    if (n_args == 4) {
        bech32_version = mp_obj_int_get_checked(args[3]);
    }

    mp_buffer_info_t buf;
    mp_get_buffer_raise(args[2], &buf, MP_BUFFER_READ);

    // low-level bech32 functions want 5-bit data unpacked into bytes. first value is
    // the version number (5 bits), and remainder is packed data.

    if (segwit_version > 16) {
        mp_raise_ValueError(MP_ERROR_TEXT("sw version"));
    }

    size_t buf_size  = sw_convert_bits_buffer_size(5, buf.len, 8, true);
    uint8_t *data    = m_new(uint8_t, buf_size + 1);
    size_t  data_len = 0;
    data[0]          = segwit_version;
    int cv_ok        = sw_convert_bits(data + 1, &data_len, 5, buf.buf, buf.len, 8, true, buf_size);

    if (cv_ok != 1) {
        m_del(uint8_t, data, buf_size + 1);
        mp_raise_ValueError(MP_ERROR_TEXT("pack fail"));
    }

    // we already prefixed the version number
    data_len += 1;

    vstr_t vstr;
    vstr_init_len(&vstr, strlen(hrp) + data_len + 8);

    int rv = bech32_encode(vstr.buf, hrp, data, data_len, bech32_version);
    if (rv != 1) {
        m_del(uint8_t, data, buf_size + 1);
        mp_raise_ValueError(MP_ERROR_TEXT("encode fail"));
    }
    m_del(uint8_t, data, buf_size + 1);
    vstr.len = strlen(vstr.buf);

    return mp_obj_new_str_from_vstr(&mp_type_str, &vstr);
}
MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(modtcc_bech32_encode_obj, 3, 4, modtcc_bech32_encode);

STATIC const mp_rom_map_elem_t modtcc_codecs_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_codecs)},
    {MP_ROM_QSTR(MP_QSTR_b58_encode), MP_ROM_PTR(&modtcc_b58_encode_obj)},
    {MP_ROM_QSTR(MP_QSTR_bech32_encode), MP_ROM_PTR(&modtcc_bech32_encode_obj)},
    {MP_ROM_QSTR(MP_QSTR_BECH32_ENCODING_BECH32), MP_ROM_INT(BECH32_ENCODING_BECH32)},
    {MP_ROM_QSTR(MP_QSTR_BECH32_ENCODING_BECH32M), MP_ROM_INT(BECH32_ENCODING_BECH32M)},
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
