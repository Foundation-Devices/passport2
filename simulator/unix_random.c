// SPDX-FileCopyrightText: 2016-2021 Damien P. George <http://micropython.org/>
//
// SPDX-License-Identifier: MIT
//
// SPDX-FileCopyrightText: © 2021 Foundation Devices, Inc. <hello@foundationdevices.com>
//
// SPDX-License-Identifier: GPL-3.0-or-later

#include <stdio.h>
#include <fcntl.h>
#include <stdint.h>
#include <unistd.h>

//
// Platform-specific random number generator: /dev/urandom
//
// compliments external/crypto/rand.c
//

// random_buffer()
//
    void
random_buffer(uint8_t *p, size_t count)
{
    static int rng_fd = -1;

    if(rng_fd < 0) {
        rng_fd = open("/dev/urandom", O_RDONLY);
    }

    int actual = read(rng_fd, p, count);

    if(actual != count) {
        fprintf(stderr, "Short read from urandom!");
        _exit(1);
    }
}

// random32()
//
    uint32_t
random32(void)
{
    uint32_t rv;

    random_buffer((uint8_t *)&rv, sizeof(uint32_t));

    return rv;
}
