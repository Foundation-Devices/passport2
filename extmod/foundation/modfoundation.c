// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// MP C foundation module, supports LCD, backlight, keypad and other devices as they are added
//
// This code is shared between the Passport hardware build and the unix simulator build.
// No hardware-specific code should be added to this file.

#include <math.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "py/obj.h"
#include "py/objstr.h"
#include "py/stream.h"
#include "py/runtime.h"

#include "image_conversion.h"

#include "hash.h"

#include "sha256.h"
#include "uECC.h"
#include "utils.h"

#include "modfoundation-bip39.h"
#include "modfoundation-qr.h"
#include "modfoundation-secp56k1.h"
#include "modfoundation-spi.h"
#include "modfoundation-ur.h"

/// package: foundation

STATIC const mp_obj_type_t mp_type_fixedbytesio;

/// def convert_rgb565_to_grayscale(rgb565: bytearray,
///                                 grayscale: bytearray,
///                                 hor_res: int,
///                                 ver_res: int) -> None:
///     '''
///     Convert the given RGB565 image to grayscale for QR search.
///     '''
STATIC mp_obj_t mod_foundation_convert_rgb565_to_grayscale(size_t n_args, const mp_obj_t *args)
{
    mp_buffer_info_t rgb565_info;
    mp_get_buffer_raise(args[0], &rgb565_info, MP_BUFFER_READ);

    mp_buffer_info_t grayscale_info;
    mp_get_buffer_raise(args[1], &grayscale_info, MP_BUFFER_WRITE);

    mp_int_t hor_res = mp_obj_get_int(args[2]);
    mp_int_t ver_res = mp_obj_get_int(args[3]);

    if (rgb565_info.len != (hor_res * ver_res * sizeof(uint16_t)))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid rgb565 buffer size"));
        return mp_const_none;
    }
    if (grayscale_info.len != (size_t)(hor_res * ver_res))
    {
        mp_raise_ValueError(MP_ERROR_TEXT("invalid grayscale buffer size"));
        return mp_const_none;
    }

    convert_rgb565_to_grayscale(rgb565_info.buf, grayscale_info.buf, hor_res, ver_res);
    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(mod_foundation_convert_rgb565_to_grayscale_obj,
                                           4,
                                           4,
                                           mod_foundation_convert_rgb565_to_grayscale);

/// def sha256(buffer, digest: bytearray) -> None
///     '''
///     Perform a sha256 hash on the given data (bytearray)
///     '''
STATIC mp_obj_t mod_foundation_sha256(mp_obj_t data, mp_obj_t digest)
{
    mp_buffer_info_t data_info;
    mp_get_buffer_raise(data, &data_info, MP_BUFFER_READ);

    mp_buffer_info_t digest_info;
    mp_get_buffer_raise(digest, &digest_info, MP_BUFFER_WRITE);

    if (digest_info.len != SHA256_BLOCK_SIZE)
    {
        mp_raise_ValueError(MP_ERROR_TEXT("Invalid digest bytearray len"));
        return mp_const_none;
    }

    SHA256_CTX ctx;
    sha256_init(&ctx);
    sha256_update(&ctx, (void *)data_info.buf, data_info.len);
    sha256_final(&ctx, digest_info.buf);

    return mp_const_none;
}
STATIC MP_DEFINE_CONST_FUN_OBJ_2(mod_foundation_sha256_obj, mod_foundation_sha256);

/// class FixedBytesIO:
///     """
///     """
typedef struct _mp_obj_fixedbytesio_t {
    mp_obj_base_t base;
    vstr_t vstr;
    mp_uint_t pos;
} mp_obj_fixedbytesio_t;

STATIC void fixedbytesio_check_open(const mp_obj_fixedbytesio_t *o) {
    if (o->vstr.buf == NULL || o->vstr.alloc == 0) {
        mp_raise_ValueError(MP_ERROR_TEXT("I/O operation on closed file"));
    }
}

/// def __init__(self, buf: bytearray) -> None:
///     """
///     """
STATIC mp_obj_t fixedbytesio_make_new(const mp_obj_type_t *type_in, size_t n_args, size_t n_kw, const mp_obj_t *args) {
    mp_buffer_info_t bufinfo;

    mp_obj_fixedbytesio_t *o = m_new_obj(mp_obj_fixedbytesio_t);
    o->base.type  = &mp_type_fixedbytesio;

    mp_get_buffer_raise(args[0], &bufinfo, MP_BUFFER_WRITE);
    vstr_init_fixed_buf(&o->vstr, bufinfo.len, bufinfo.buf);
    return MP_OBJ_FROM_PTR(o);
}

STATIC void fixedbytesio_print(const mp_print_t *print, mp_obj_t self_in, mp_print_kind_t kind) {
    (void)kind;
    mp_printf(print, "<foundation.FixedBytesIO 0x%x>", MP_OBJ_TO_PTR(self_in));
}

STATIC mp_uint_t fixedbytesio_read(mp_obj_t o_in, void *buf, mp_uint_t size, int *errcode) {
    mp_obj_fixedbytesio_t *o = MP_OBJ_TO_PTR(o_in);
    fixedbytesio_check_open(o);
    if (o->vstr.len <= o->pos) {
        return 0;
    }

    mp_uint_t remaining = o->vstr.len - o->pos;
    if (size > remaining) {
        size = remaining;
    }
    memcpy(buf, o->vstr.buf + o->pos, size);
    o->pos += size;
    return size;
}

STATIC mp_uint_t fixedbytesio_write(mp_obj_t o_in, const void *buf, mp_uint_t size, int *errcode) {
    mp_obj_fixedbytesio_t *o = MP_OBJ_TO_PTR(o_in);
    fixedbytesio_check_open(o);

    mp_uint_t new_pos = o->pos + size;
    if (new_pos < size || new_pos > o->vstr.alloc) {
        *errcode = MP_EFBIG;
        return MP_STREAM_ERROR;
    }
    
    // If there was a seek past EOF, clear the hole
    if (o->pos > o->vstr.len) {
        memset(o->vstr.buf + o->vstr.len, 0, o->pos - o->vstr.len);
    }
    memcpy(o->vstr.buf + o->pos, buf, size);
    o->pos = new_pos;
    if (new_pos > o->vstr.len) {
        o->vstr.len = new_pos;
    }

    return size;
}

STATIC mp_uint_t fixedbytesio_ioctl(mp_obj_t o_in, mp_uint_t request, uintptr_t arg, int *errcode) {
    mp_obj_fixedbytesio_t *o = MP_OBJ_TO_PTR(o_in);
    switch (request) {
        case MP_STREAM_SEEK: {
            struct mp_stream_seek_t *s = (struct mp_stream_seek_t *)arg;
            mp_uint_t ref = 0;
            switch (s->whence) {
                case MP_SEEK_CUR:
                    ref = o->pos;
                    break;
                case MP_SEEK_END:
                    ref = o->vstr.len;
                    break;
            }
            mp_uint_t new_pos = ref + s->offset;

            // For MP_SEEK_SET, offset is unsigned
            if (s->whence != MP_SEEK_SET && s->offset < 0) {
                if (new_pos > ref) {
                    // Negative offset from SEEK_CUR or SEEK_END went past 0.
                    // CPython sets position to 0, POSIX returns an EINVAL error
                    new_pos = 0;
                }
            } else if (new_pos < ref) {
                // positive offset went beyond the limit of mp_uint_t
                *errcode = MP_EINVAL;  // replace with MP_EOVERFLOW when defined
                return MP_STREAM_ERROR;
            }
            s->offset = o->pos = new_pos;
            return 0;
        }
        case MP_STREAM_FLUSH:
            return 0;
        case MP_STREAM_CLOSE:
            vstr_clear(&o->vstr);
            o->vstr.alloc = 0;
            o->vstr.len = 0;
            o->pos = 0;
            return 0;
        default:
            *errcode = MP_EINVAL;
            return MP_STREAM_ERROR;
    }
}

STATIC mp_obj_t fixedbytesio_getvalue(mp_obj_t self_in) {
    mp_obj_fixedbytesio_t *self = MP_OBJ_TO_PTR(self_in);
    return mp_obj_new_bytearray_by_ref(self->vstr.len, self->vstr.buf);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_1(fixedbytesio_getvalue_obj, fixedbytesio_getvalue);

STATIC mp_obj_t fixedbytesio___exit__(size_t n_args, const mp_obj_t *args) {
    (void)n_args;
    return mp_stream_close(args[0]);
}
STATIC MP_DEFINE_CONST_FUN_OBJ_VAR_BETWEEN(fixedbytesio___exit___obj, 4, 4, fixedbytesio___exit__);

STATIC const mp_rom_map_elem_t fixedbytesio_locals_dict_table[] = {
    { MP_ROM_QSTR(MP_QSTR_read), MP_ROM_PTR(&mp_stream_read_obj) },
    { MP_ROM_QSTR(MP_QSTR_readinto), MP_ROM_PTR(&mp_stream_readinto_obj) },
    { MP_ROM_QSTR(MP_QSTR_readline), MP_ROM_PTR(&mp_stream_unbuffered_readline_obj) },
    { MP_ROM_QSTR(MP_QSTR_write), MP_ROM_PTR(&mp_stream_write_obj) },
    { MP_ROM_QSTR(MP_QSTR_seek), MP_ROM_PTR(&mp_stream_seek_obj) },
    { MP_ROM_QSTR(MP_QSTR_tell), MP_ROM_PTR(&mp_stream_tell_obj) },
    { MP_ROM_QSTR(MP_QSTR_flush), MP_ROM_PTR(&mp_stream_flush_obj) },
    { MP_ROM_QSTR(MP_QSTR_close), MP_ROM_PTR(&mp_stream_close_obj) },
    { MP_ROM_QSTR(MP_QSTR_getvalue), MP_ROM_PTR(&fixedbytesio_getvalue_obj) },
    { MP_ROM_QSTR(MP_QSTR___enter__), MP_ROM_PTR(&mp_identity_obj) },
    { MP_ROM_QSTR(MP_QSTR___exit__), MP_ROM_PTR(&fixedbytesio___exit___obj) },
};


STATIC MP_DEFINE_CONST_DICT(fixedbytesio_locals_dict, fixedbytesio_locals_dict_table);

STATIC const mp_stream_p_t fixedbytesio_stream_p = {
    .read = fixedbytesio_read,
    .write = fixedbytesio_write,
    .ioctl = fixedbytesio_ioctl,
};

STATIC const mp_obj_type_t mp_type_fixedbytesio = {
    { &mp_type_type },
    .name = MP_QSTR_FixedBytesIO,
    .print = fixedbytesio_print,
    .make_new = fixedbytesio_make_new,
    .getiter = mp_identity_getiter,
    .iternext = mp_stream_unbuffered_iter,
    .protocol = &fixedbytesio_stream_p,
    .locals_dict = (mp_obj_dict_t *)&fixedbytesio_locals_dict,
};

/* Module Global configuration */
/* Define all properties of the module.
 * Table entries are key/value pairs of the attribute name (a string)
 * and the MicroPython object reference.
 * All identifiers and strings are written as MP_QSTR_xxx and will be
 * optimized to word-sized integers by the build system (interned strings).
 */

STATIC const mp_rom_map_elem_t foundation_module_globals_table[] = {
    {MP_ROM_QSTR(MP_QSTR___name__), MP_ROM_QSTR(MP_QSTR_foundation)},
    {MP_ROM_QSTR(MP_QSTR_FixedBytesIO), MP_ROM_PTR(&mp_type_fixedbytesio)},
    {MP_ROM_QSTR(MP_QSTR_bip39), MP_ROM_PTR(&mod_foundation_bip39_module)},
    {MP_ROM_QSTR(MP_QSTR_qr), MP_ROM_PTR(&mod_foundation_qr_module)},
    {MP_ROM_QSTR(MP_QSTR_secp256k1), MP_ROM_PTR(&mod_foundation_secp256k1_module)},
    {MP_ROM_QSTR(MP_QSTR_ur), MP_ROM_PTR(&mod_foundation_ur_module)},
    {MP_ROM_QSTR(MP_QSTR_convert_rgb565_to_grayscale), MP_ROM_PTR(&mod_foundation_convert_rgb565_to_grayscale_obj)},
    {MP_ROM_QSTR(MP_QSTR_sha256), MP_ROM_PTR(&mod_foundation_sha256_obj)},
};
STATIC MP_DEFINE_CONST_DICT(foundation_module_globals, foundation_module_globals_table);

/* Define module object. */
const mp_obj_module_t foundation_user_cmodule = {
    .base = {&mp_type_module},
    .globals = (mp_obj_dict_t *)&foundation_module_globals,
};

MP_REGISTER_MODULE(MP_QSTR_foundation, foundation_user_cmodule, PASSPORT_FOUNDATION_ENABLED);
