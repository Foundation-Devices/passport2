/*
 * This file is part of the MicroPython project, http://micropython.org/
 *
 * The MIT License (MIT)
 *
 * Copyright (c) 2013-2019 Damien P. George
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy
 * of this software and associated documentation files (the "Software"), to deal
 * in the Software without restriction, including without limitation the rights
 * to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 * copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in
 * all copies or substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 * FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 * AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 * LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 * THE SOFTWARE.
 */

#include <stdlib.h>
#include "py/runtime.h"
#include "py/binary.h"
#include "py/objarray.h"
#include "py/mperrno.h"
#include "extmod/vfs.h"

#include "extmod/foundation/modlogging.h"

#if MICROPY_VFS

#define NUM_BUFS_TO_COMPARE 3  //consider 2 for less unnecessary failures
#define MAX_READ_ATTEMPTS   21

void mp_vfs_blockdev_init(mp_vfs_blockdev_t *self, mp_obj_t bdev) {
    mp_load_method(bdev, MP_QSTR_readblocks, self->readblocks);
    mp_load_method_maybe(bdev, MP_QSTR_writeblocks, self->writeblocks);
    mp_load_method_maybe(bdev, MP_QSTR_ioctl, self->u.ioctl);
    if (self->u.ioctl[0] != MP_OBJ_NULL) {
        // Device supports new block protocol, so indicate it
        self->flags |= MP_BLOCKDEV_FLAG_HAVE_IOCTL;
    } else {
        // No ioctl method, so assume the device uses the old block protocol
        mp_load_method_maybe(bdev, MP_QSTR_sync, self->u.old.sync);
        mp_load_method(bdev, MP_QSTR_count, self->u.old.count);
    }
}

int internal_read(mp_vfs_blockdev_t *self, size_t block_num, size_t num_blocks, uint8_t *buf) {
    if (self->flags & MP_BLOCKDEV_FLAG_NATIVE) {
        mp_uint_t (*f)(uint8_t *, uint32_t, uint32_t) = (void *)(uintptr_t)self->readblocks[2];
        return f(buf, block_num, num_blocks);
    } else {
        mp_obj_array_t ar = {{&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, num_blocks *self->block_size, buf};
        self->readblocks[2] = MP_OBJ_NEW_SMALL_INT(block_num);
        self->readblocks[3] = MP_OBJ_FROM_PTR(&ar);
        mp_obj_t res = mp_call_method_n_kw(2, 0, self->readblocks);

        // readblocks returns true for success
        bool err = !mp_obj_is_true(res);
        if (err) {
            return 1;
        }
        return 0;
    }
}

int mp_vfs_blockdev_read(mp_vfs_blockdev_t *self, size_t block_num, size_t num_blocks, uint8_t *buf) {

    int result = 1, i = 0;
    for (; i < MAX_READ_ATTEMPTS && result != 0; i++) {
        result = internal_read(self, block_num, num_blocks, buf);
        if (result != 0) {
            write_to_log("failed read %d\n", i);
        }
    }
    write_to_log("final result: %d\n", result);
    return result;

    // original function
    /* if (self->flags & MP_BLOCKDEV_FLAG_NATIVE) {
        mp_uint_t (*f)(uint8_t *, uint32_t, uint32_t) = (void *)(uintptr_t)self->readblocks[2];
        return f(buf, block_num, num_blocks);
    } else {
        mp_obj_array_t ar = {{&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, num_blocks *self->block_size, buf};
        self->readblocks[2] = MP_OBJ_NEW_SMALL_INT(block_num);
        self->readblocks[3] = MP_OBJ_FROM_PTR(&ar);
        mp_call_method_n_kw(2, 0, self->readblocks);
        // TODO handle error return
        return 0;
    } */

    // 3 in a row function
    /* size_t buf_size = num_blocks * self->block_size;
    uint8_t * compare_buffers[NUM_BUFS_TO_COMPARE];

    for (int i = 0; i < NUM_BUFS_TO_COMPARE; i++) {
        compare_buffers[i] = m_new(uint8_t, buf_size);
        if (compare_buffers[i] == NULL) {
            // Handle memory allocation failure
            for (int j = 0; j < i; j++) {
                m_del(uint8_t, compare_buffers[j], buf_size);
            }
            return 1;  // Return with error
        }
        memset(compare_buffers[i], 0, sizeof(uint8_t) * buf_size);
    }

    uint8_t num_reads = 0;
    uint8_t curr_idx = 0;
    int res = 1;  // If there's never a successful read, return an error

    while (true) {
        bool retry = false;
        int new_res = internal_read(self, block_num, num_blocks, compare_buffers[curr_idx]);
        if (new_res == 0) {
            res = 0;
        }

        curr_idx = (curr_idx + 1) % NUM_BUFS_TO_COMPARE;
        num_reads++;

        if (num_reads >= NUM_BUFS_TO_COMPARE) {
            for (int i = 0; i < NUM_BUFS_TO_COMPARE - 1; i++) {
                if (memcmp(compare_buffers[i], compare_buffers[i + 1], buf_size) != 0) {
                    retry = true;
                    break;
                }
            }
        }

        if (num_reads < NUM_BUFS_TO_COMPARE || (retry && num_reads < MAX_READ_ATTEMPTS)) {
            continue;
        } else {

            if (!retry) {
                memcpy(buf, compare_buffers[0], buf_size);
                break;
            }

            // Find and copy the first non-zero buffer
            bool nonzero = false;
            size_t i = 0;
            for (i = 0; i < NUM_BUFS_TO_COMPARE && !nonzero; i++) {
                for (size_t j = 0; j < buf_size; j++) {
                    if (compare_buffers[i][j] != 0) {
                        nonzero = true;
                        break;
                    }
                }
            }

            // This should never happen, but if all are 0s, return first
            if (i == NUM_BUFS_TO_COMPARE) {
                i = 0;
            }

            memcpy(buf, compare_buffers[i], buf_size);
            break;
        }
    }

    for (int i = 0; i < NUM_BUFS_TO_COMPARE; i++) {
        m_del(uint8_t, compare_buffers[i], buf_size);
    }

    return res; */
}

int mp_vfs_blockdev_read_ext(mp_vfs_blockdev_t *self, size_t block_num, size_t block_off, size_t len, uint8_t *buf) {
    mp_obj_array_t ar = {{&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, len, buf};
    self->readblocks[2] = MP_OBJ_NEW_SMALL_INT(block_num);
    self->readblocks[3] = MP_OBJ_FROM_PTR(&ar);
    self->readblocks[4] = MP_OBJ_NEW_SMALL_INT(block_off);
    mp_obj_t ret = mp_call_method_n_kw(3, 0, self->readblocks);
    if (ret == mp_const_none) {
        return 0;
    } else {
        return MP_OBJ_SMALL_INT_VALUE(ret);
    }
}

int mp_vfs_blockdev_write(mp_vfs_blockdev_t *self, size_t block_num, size_t num_blocks, const uint8_t *buf) {
    if (self->writeblocks[0] == MP_OBJ_NULL) {
        // read-only block device
        return -MP_EROFS;
    }

    if (self->flags & MP_BLOCKDEV_FLAG_NATIVE) {
        mp_uint_t (*f)(const uint8_t *, uint32_t, uint32_t) = (void *)(uintptr_t)self->writeblocks[2];
        return f(buf, block_num, num_blocks);
    } else {
        mp_obj_array_t ar = {{&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, num_blocks *self->block_size, (void *)buf};
        self->writeblocks[2] = MP_OBJ_NEW_SMALL_INT(block_num);
        self->writeblocks[3] = MP_OBJ_FROM_PTR(&ar);
        mp_call_method_n_kw(2, 0, self->writeblocks);
        // TODO handle error return
        return 0;
    }
}

int mp_vfs_blockdev_write_ext(mp_vfs_blockdev_t *self, size_t block_num, size_t block_off, size_t len, const uint8_t *buf) {
    if (self->writeblocks[0] == MP_OBJ_NULL) {
        // read-only block device
        return -MP_EROFS;
    }

    mp_obj_array_t ar = {{&mp_type_bytearray}, BYTEARRAY_TYPECODE, 0, len, (void *)buf};
    self->writeblocks[2] = MP_OBJ_NEW_SMALL_INT(block_num);
    self->writeblocks[3] = MP_OBJ_FROM_PTR(&ar);
    self->writeblocks[4] = MP_OBJ_NEW_SMALL_INT(block_off);
    mp_obj_t ret = mp_call_method_n_kw(3, 0, self->writeblocks);
    if (ret == mp_const_none) {
        return 0;
    } else {
        return MP_OBJ_SMALL_INT_VALUE(ret);
    }
}

mp_obj_t mp_vfs_blockdev_ioctl(mp_vfs_blockdev_t *self, uintptr_t cmd, uintptr_t arg) {
    if (self->flags & MP_BLOCKDEV_FLAG_HAVE_IOCTL) {
        // New protocol with ioctl
        self->u.ioctl[2] = MP_OBJ_NEW_SMALL_INT(cmd);
        self->u.ioctl[3] = MP_OBJ_NEW_SMALL_INT(arg);
        return mp_call_method_n_kw(2, 0, self->u.ioctl);
    } else {
        // Old protocol with sync and count
        switch (cmd) {
            case MP_BLOCKDEV_IOCTL_SYNC:
                if (self->u.old.sync[0] != MP_OBJ_NULL) {
                    mp_call_method_n_kw(0, 0, self->u.old.sync);
                }
                break;

            case MP_BLOCKDEV_IOCTL_BLOCK_COUNT:
                return mp_call_method_n_kw(0, 0, self->u.old.count);

            case MP_BLOCKDEV_IOCTL_BLOCK_SIZE:
                // Old protocol has fixed sector size of 512 bytes
                break;

            case MP_BLOCKDEV_IOCTL_INIT:
                // Old protocol doesn't have init
                break;
        }
        return mp_const_none;
    }
}

#endif // MICROPY_VFS
