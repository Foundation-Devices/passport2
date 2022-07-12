// SPDX-FileCopyrightText: 2020 Foundation Devices, Inc. <hello@foundationdevices.com>
// SPDX-License-Identifier: GPL-3.0-or-later
//
// Utility functions

#include <stdint.h>
#include <stdio.h>

void dump_buf(uint8_t* buf, int len) {
    for (int i = 0; i < len; i++) {
        printf("%02x ", buf[i]);
        i++;
        if ((i % 16 == 0) || (i == len - 1)) {
            printf("\n");
        }
    }
}